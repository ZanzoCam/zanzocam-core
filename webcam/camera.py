import os
import math
import json
import time
import shutil
import requests
import datetime
import textwrap
import traceback
import subprocess
from pathlib import Path
from picamera import PiCamera
from PIL import Image, ImageFont, ImageDraw


# Global vars
path = Path(__file__).parent
local_images_path = path / "overlays"


def main():
    # Boots up and checks itself
    log("Start")
    status = collect_stats()
    
    # Get configuration
    conf = get_configuration()
    if conf is not None:
    
        # Send logs of the previous run
        server_url = conf.get("server_url")
        server_user = conf.get("server_username")
        server_pwd = conf.get("server_password")
        send_logs(server_url, server_user, server_pwd)
        
        # Process and send the picture
        take_picture(conf)
        
    print("\n==========================================\n")
    
    
def log(msg):
    print(f"{datetime.datetime.now()} -> {msg}")


def decode_json_numbers(json):
    for k, v in json.items():
        try:
            if isinstance(v, dict):
                json[k] = decode_json_numbers(v)
            if isinstance(v, str):
                if v == "false":
                    value = False
                if v == "true":
                    value = True
                value = float(v)
                value = int(v)
                json[k] = value
        except ValueError:
            pass
    return json


def collect_stats():
    """ 
    Print system statistics in the logs. 
    """
    log("Collecting system statistics")
    stats = {}
    
    # Version
    try:
        with open("../zanzocam/.VERSION") as v:
            stats["version"] = v.readline().strip()
    except Exception as e:
        log("Could not get version information.")
        traceback.print_exc()

    # Uptime
    try:
        uptime_proc = subprocess.Popen(['uptime', '-s'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        stdout, stderr = uptime_proc.communicate()
        stats['uptime'] = stdout.decode('utf-8').strip()
        # TODO convertin timedelta and show the span (like 5 days 3 hours 27 minutes)
    except Exception as e:
        log("ERROR! Could not get uptime information.")
        traceback.print_exc()

    # Autohotspot
    try:
        hotspot_proc = subprocess.run(["/usr/bin/sudo", "/usr/bin/autohotspot"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not hotspot_proc:
            raise ValueError("The autohotspot script failed to run or returned an exception.")
        stats['autohotspot'] = True
    except Exception as e:
        log("ERROR! The hotspot script failed to run.")
        traceback.print_exc()
        stats["autohotspot"] = False

    # WiFi SSID
    try:
        wifi_proc = subprocess.Popen(['/usr/sbin/iwgetid', '-r'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        stdout, stderr = wifi_proc.communicate()
        stats['WiFi SSID'] = stdout.decode('utf-8').strip()
    except Exception as e:
        log("ERROR! Could not retrieve WiFi information.")
        traceback.print_exc()

    # Ensure Internet connectivity - TODO

    # Log the outcomes
    stats_string = ""
    for stat, value in stats.items():
        stats_string += f" - {stat}: {value}\n"
    log(f"System statistics:\n{stats_string}")

    return stats


def get_configuration():
    """ 
    Download the new configuration files from the server.
    If the download fails for any reason, logs the error and then fallback to
    the backup of the previous configuration file.
    """
    log(f"Fetching new configuration")
            
    old_conf = {}
    try:
        # Get the server data from the old configuration file
        with open(path / "configuration.json", 'r') as c:
            old_conf = json.load(c)
        url = old_conf.get("server_url")
        user = old_conf.get("server_username")
        pwd = old_conf.get("server_password")
        log(f"Server URL: {url}")
        
        # Backup the old config file
        shutil.copy(path / "configuration.json", path / "configuration.prev.json")

    except Exception as e:
        log("ERROR! Something went wrong loading the old configuration file.")
        traceback.print_exc()
        log("THIS ERROR IS FATAL: exiting.")
        return None
    
    try:
        # Fetch the new config
        if user:
            raw_response = requests.get(url, auth=requests.auth.HTTPBasicAuth(user, pwd))
        else:
            raw_response = requests.get(url)

        # Write the new config into the configuration file                    
        response = json.loads(raw_response.content.decode('utf-8'))
        new_conf = response["configuration"]
        new_conf = decode_json_numbers(new_conf)  # The configuration file will contain strings in place of numbers!
        
        with open(path / "configuration.json", 'w') as c:
            json.dump(new_conf, c, indent=4)

        log("Configuration downloaded successfully:")
        print(json.dumps(new_conf, indent=4))
        
        # Download any new image
        # TODO cleaup old icons? Requires backup, delete, check for errors and potentially restore if something went wrong
        remote_images_path = new_conf['server_url'] + "config/images/"  # TODO make configurable?
        
        new_images = response["images"]
        for image in new_images:
            if True: #not os.path.exists(local_images_path / image):                
                
                r = requests.get(f"{remote_images_path}{image}", stream=True, auth=requests.auth.HTTPBasicAuth(user, pwd))
                if r.status_code == 200:
                    r.raw.decode_content = True

                    with open(local_images_path / image ,'wb') as f:
                        shutil.copyfileobj(r.raw, f)

                    log(f"New overlay image downloaded: {image}")

                else:
                    log(f"ERROR! New overlay image failed to download: {image}")
                    log(f"Response status code: {r.status_code}")
                    log("Replacing it with empty image file.")
                    shutil.copy2(path / "fallback-pixel.png", local_images_path / image)          
        
        # Apply the new system configuration if needed
        log("Applying new system settings from the configuration file...")
        try:  
            apply_system_settings(new_conf)
            
        # Try to restore the old system settings if something goes wrong
        except Exception as e:
            log("ERROR! Something happened while applying the system "
                "settings from the new configuration file.")
            traceback.print_exc()
            log("Re-applying the old system configuration:")
            try:  
                apply_system_settings(old_conf)
            except Exception as e:
                log("ERROR! Something unexpected occurred while re-applyign the "
                    "old system settings!")
                traceback.print_exc()
                log("THIS ERROR IS FATAL: the webcam might be in an inconsistent state."
                    "ZANZOCAM might need manual intervention at this point.")
                    
        # Return the downloaded data
        return new_conf
        
    except Exception as e:
        log("ERROR! Something went wrong fetching the new config file from the server.")
        traceback.print_exc()
        log("The server replied:")
        print(vars(raw_response))  
        log("Falling back to old configuration file.") 
        print(json.dumps(old_conf, indent=4))
        return old_conf  


def apply_system_settings(conf):
    """ 
    Modifies the system according to the new configuration file content.
    """    
    # Create the crontab
    cron = conf.get("crontab", {})
    cron_string = " ".join([
        cron.get('minute', '*'),
        cron.get('hour', '*'),
        cron.get('day', '*'),
        cron.get('month', '*'),
        cron.get('weekday', '*')
    ])
    with open(".tmp-cronjob-file", 'w') as d:
        d.writelines(textwrap.dedent(f"""
            # ZANZOCAM - shoot pictures
            {cron_string} zanzocam-bot cd /home/zanzocam-bot/webcam && /home/zanzocam-bot/webcam/venv/bin/python3 /home/zanzocam-bot/webcam/camera.py >> /home/zanzocam-bot/webcam/logs.txt 2>&1
            """))
            
    # Backup the old crontab in the home
    backup_cron = subprocess.run([
        "/usr/bin/sudo", "mv", "/etc/cron.d/zanzocam", "/home/zanzocam-bot/.crontab.bak"], 
        stdout=subprocess.PIPE)
    if not backup_cron:
        log("ERROR! Something went wrong creating a backup for the cron file.")
        log("No backup is created.")
        
    # Move new cron file into cron folder
    create_cron = subprocess.run([
        "/usr/bin/sudo", "mv", ".tmp-cronjob-file", "/etc/cron.d/zanzocam"], 
        stdout=subprocess.PIPE)
    if not create_cron:
        log("ERROR! Something went wrong creating the new cron file.")
        log("The old cron file should be unaffected.")

    # Give ownership of the new crontab file to root
    chown_cron = subprocess.run([
        "/usr/bin/sudo", "chown", "root:root", "/etc/cron.d/zanzocam"], 
        stdout=subprocess.PIPE)
    # if it fails, start recovery procedure by trying to write back the old crontab
    if not chown_cron:
        log("ERROR! Something went wrong changing the owner of the crontab!")
        log("Trying to restore the crontab using the backup")
        log("+++++++++++++++++++++++++++++++++++++++++++")
        if not backup_cron:
            log("ERROR! The backup was not created!")
            log("THIS ERROR IS FATAL: the crontab might not trigger anymore.")
            log("ZANZOCAM might need manual intervention.")
        else:
            restore_cron = subprocess.run([
                "/usr/bin/sudo", "mv", "/home/zanzocam-bot/.crontab.bak", "/etc/cron.d/zanzocam"], 
                stdout=subprocess.PIPE)
            if not restore_cron:
                log("ERROR! Something went wrong restoring the cron file from its backup!")
                log("THIS ERROR IS FATAL: the crontab might not trigger anymore.")
                log("ZANZOCAM might need manual intervention.")
            else:
                log("cron file restored successfully.")
                log("Please investigate the cause of the issue!")
        log("+++++++++++++++++++++++++++++++++++++++++++")
            


def send_logs(url, user=None, pwd=None):
    """ 
    Send the logs to the server. 
    Tries to never fail in order not to break the main routine if something 
    goes wrong at this stage (even though it's a worrying sign).
    """
    log(f"Uploading logs to {url}")
        
    # Load the logs content
    logs = " ==> No logs found!! <== "
    try:
        logs_file = path/"logs.txt"
        
        if not os.path.exists(logs_file):
            open(logs_file, 'w').close()
            
        with open(logs_file, "r") as l:
            logs = l.readlines()
    except Exception as e:
        log("ERROR! Something happened opening the logs file.")
        traceback.print_exc()
        log("This error will be ignored.")
        return

    # Prepare and send the request
    try:
        data = {'logs': "".join(logs)}
        if user:
            raw_response = requests.post(url, data=data, 
                                    auth=requests.auth.HTTPBasicAuth(user, pwd))
        else:
            raw_response = requests.post(url, data=data)
        response = json.loads(raw_response.content.decode("utf-8"))
        
        # Make sure the server did not return an error
        reply = response.get("logs", "No field named 'logs' in the response")
        if reply != "":
            log("ERROR! The server replied with an error.")
            log("The server replied:")
            log(vars(raw_response))  
            log("The error is " + str(reply))
            log("This error will be ignored.")
            return
            
        log("Logs uploaded successfully.")
    
    except Exception as e:
        log("ERROR! Something happened uploading the logs file.")
        traceback.print_exc()
        log("This error will be ignored.")
        return



def take_picture(conf, retrying=False):
    """
    Takes the picture, renders the elements on and sends it to the server.
    Handles failures internally.
    """
    try:
        # Shoot picture
        log("Taking photo")
        raw_pic_name = shoot_picture(conf.get("image", {}))
        
        # Add overlays
        log("Rendering photo")
        final_pic_name = process_picture(raw_pic_name, conf.get("image", {}), conf.get("overlays", {}))
        
        # Upload picture
        log("Uploading photo")
        server_url = conf.get("server_url")
        server_user = conf.get("server_username")
        server_pwd = conf.get("server_password")
        send_picture(final_pic_name, server_url, server_user, server_pwd)
        
        # Clean up picture if everything worked out
        log("Cleaning up")
        os.remove(raw_pic_name)
        os.remove(final_pic_name)
        log("Cleanup done")
        
    except Exception as e:
        if not retrying:
            # Try again using the old config file
            log("ERROR! Something unexpected happened during the main routine!")
            traceback.print_exc()
            log("+++++++++++++++++++++++++++++++++++++++++++")
            log("Discarding newest configuration and restoring the previous values.")
            
            shutil.copy(path / "configuration.prev.json", path / "configuration.json")
            conf = {}
            with open(path / "configuration.json", 'r') as c:
                conf = json.load(c)
            
            take_picture(conf, retrying=True)
            log("+++++++++++++++++++++++++++++++++++++++++++")
            return 
            
        # That's the second run that failed: give up.
        log("ERROR! Something happened while running with the old configuration file too!")
        log("The exception is: " + str(e))
        traceback.print_exc()
        log("THIS ERROR IS FATAL: giving up.")
        return


def shoot_picture(image_conf):
    """ 
    Shoots the picture and returns the name of the saved image.
    """
    camera = PiCamera()
    camera.resolution = (int(image_conf.get("width", 100)), int(image_conf.get("height", 100)))
    camera.vflip = image_conf.get("ver_flip", False)
    camera.hflip = image_conf.get("hor_flip", False)
    camera.rotation = int(image_conf.get("rotation", 0))
    image_name = '.temp_image.jpg'
    camera.capture(image_name)
    camera.close()
    return image_name


def _process_text(font, user_text, max_line_length):
    """ 
    Measures and insert returns into the text to make it fit into the image.
    """
    # Insert as many returns as needed to make the text fit.
    lines = []
    for line in user_text.split("\n"):
        if font.getsize(line)[0] <= max_line_length:
            lines.append(line)
        else:
            new_line = ""
            for word in line.split(" "):
                if font.getsize(new_line + word)[0] <= max_line_length:
                    new_line = new_line + word + " "
                else:
                    lines.append(new_line)
                    new_line = word + " "
            if new_line != "":
                lines.append(new_line)
    text = '\n'.join(lines)

    # Create a temporary image to measure the text size
    _scratch = Image.new("RGBA", (1,1))
    _draw = ImageDraw.Draw(_scratch)

    return text, _draw.textsize(text, font)


def _prepare_text_overlay(conf, picture_size):
    """ 
    Prepares an overlay containing text.
    Might return None in case of issues. 
    """
    try:
        # Creates the font and calculate the line height
        font_size = conf.get("font_size", 25)
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        line_height = font.getsize("a")[1] * 1.5

        # Calculate the padding as a percentage of the line height
        padding_ratio = conf.get("padding_ratio", 0.2)
        padding = math.ceil(line_height*padding_ratio)

        # Replace %%TIME and %%DATE with respective values
        user_text = conf.get("text", "~~~ DEFAULT TEXT ~~~")
        time_format = conf.get("time_format", "%H:%M:%S")
        user_text = user_text.replace("%%TIME", datetime.datetime.now().strftime(time_format))
        date_format = conf.get("date_format", "%Y-%m-%d")
        user_text = user_text.replace("%%DATE", datetime.datetime.now().strftime(date_format))

        # Calculate the dimension of the text with the padding added
        text, text_size = _process_text(font, user_text, picture_size[0])
        text_size = (text_size[0] + padding * 2, text_size[1] + padding * 2)

        # Creates the image
        font_color = conf.get("font_color", (0, 0, 0))
        background_color = conf.get("background_color", (255, 255, 255, 0))
        label = Image.new("RGBA", text_size, color=background_color)
        draw = ImageDraw.Draw(label)
        draw.text((padding, padding, padding), text, font_color, font=font)

        return label

    except Exception as e:
        log("ERROR! Something unexpected happened while generating text the overlay. "+
        "This overlay will be skipped.")
        traceback.print_exc()
        return None


def _prepare_image_overlay(conf):
    """ 
    Prepares an overlay containing an image.
    Might return None in case of issues. 
    """
    picture_name = local_images_path / conf.get("image")

    if not picture_name:
        log(f"ERROR! This image overlay does not contain the image path. "
        "This overlay will be skipped.")
        return None

    try:
        picture = Image.open(path / picture_name).convert("RGBA")
    except Exception as e:
        log(f"ERROR! Image '{picture_name}' not found. "
        "This overlay will be skipped.")
        traceback.print_exc()
        return None
    
    try:
        # Calculate new dimension, retaining aspect ratio if necessary
        width = conf.get("width")
        height = conf.get("height")
        if width and not height:
            old_aspect_ratio = picture.size[0]/picture.size[1]
            height = math.ceil(width/old_aspect_ratio)
        if not width and height:
            old_aspect_ratio = picture.size[1]/picture.size[0]
            width = math.ceil(height/old_aspect_ratio)

        picture = picture.resize((width, height))

        padding_ratio = conf.get("padding_ratio", 0.2)
        padding_width = math.ceil(width*padding_ratio)
        padding_height = math.ceil(height*padding_ratio)

        image_size = (width+padding_width*2, height+padding_height*2)
        background_color = conf.get("background_color", (0, 0, 0, 0))
        image = Image.new("RGBA", image_size, color=background_color)
        image.paste(picture, (padding_width, padding_height), mask=picture)

        return image
        
    except Exception as e:
        log("ERROR! Something unexpected happened while generating the image overlay. "+
            "This overlay will be skipped.")
        traceback.print_exc()
        return None


def process_picture(raw_picture_name, image_conf, overlays_conf):
    """ 
    Renders text and images over the picture and saves the resulting image
    with the proper name and format.
    """
    # Open and measures the picture
    picture = Image.open(raw_picture_name).convert("RGBA")
    picture_size = picture.size

    # Creates the components to overlay
    pieces_to_layout = []
    for piece_position, piece_conf in overlays_conf.items():
        try:
            log(f"Processing overlay {piece_position}")
        
            kind = piece_conf.get("type", "none")
            if kind == "text":
                overlay = _prepare_text_overlay(piece_conf, picture_size)
                if overlay is not None:
                    pieces_to_layout.append((piece_position, piece_conf, overlay))

            elif kind == "image":
                overlay = _prepare_image_overlay(piece_conf)
                if overlay is not None:
                    pieces_to_layout.append((piece_position, piece_conf, overlay))
        
            elif kind == "none":
                log(f"No overlay specified for position {piece_position}.")
            else:
                log(f"ERROR! Overlay name '{kind}' not recognized. Valid names: "
                "text, image. This overlay will be skipped.")

        except Exception as e:
            log(f"ERROR! Something happened processing the overlay {piece_position}. This overlay will be skipped.")
            traceback.print_exc()

    # Calculate borders to add to the picture according to the size of 
    # the out-of-picture overlays
    border_top = 0
    border_bottom = 0
    for pos, o_conf, overlay in pieces_to_layout:
        if not o_conf.get("over_the_picture", False):
            if "top" in pos:
                border_top = max(border_top, overlay.size[1])
            else:
                border_bottom = max(border_bottom, overlay.size[1])

    # Generate canvas of the correct size
    image_size = (picture_size[0], picture_size[1]+border_top+border_bottom)
    image_background_color = image_conf.get("background_color", (0,0,0,0))
    image = Image.new("RGBA", image_size, color=image_background_color)

    # Add the picture on the canvas
    image.paste(picture, (0, border_top))

    # Add the overlays on the canvas in the right position
    for pos, o_conf, overlay in pieces_to_layout:
        over_picture = o_conf.get("over_the_picture", False)
        x, y = 0, 0
        if "left" in pos:
            x = 0
        if "right" in pos:
            x = image.size[0]-overlay.size[0]
        if "center" in pos:
            x = int((image.size[0]-overlay.size[0])/2)
        if "top" in pos:
            if over_picture:
                y = border_top
            else:
                y = 0
        if "bottom" in pos:
            if over_picture:
                y = image.size[1]-overlay.size[1]-border_bottom
            else:
                y = image.size[1]-overlay.size[1]
        image.paste(overlay, (x, y), mask=overlay)  # mask is to allow for transparent images

    # Assemble the image name
    image_name = image_conf.get("name", "image")
    image_extension = image_conf.get("extension", "jpg")
    if image_conf.get("add_date_to_name", True):
        image_name += "_" + datetime.datetime.now().strftime("%Y-%m-%d")
    if image_conf.get("add_time_to_name", True):
        image_name += "_" + datetime.datetime.now().strftime("%H:%M:%S")
    image_name = image_name + "." + image_extension
    
    # Save the image appropriately
    if image_extension.lower() == "jpg" or image_extension.lower() == "jpeg":
        quality = image_conf.get("jpeg_quality", 100)
        subsampling = image_conf.get("jpeg_subsampling", 0)
        image = image.convert('RGB')
        image.save(image_name, format='JPEG', subsampling=subsampling, quality=quality)
   
    else:
        image.save(image_name)
    
    return image_name


def send_picture(image_name, url, user=None, pwd=None) -> bool:
    """
    Send POST request with the image to the server.
    """
    raw_response = None
    try:
        files = {'photo': open(image_name, 'rb')}
    
        if user:
            raw_response = requests.post(url, files=files, 
                                    auth=requests.auth.HTTPBasicAuth(user, pwd))
        else:
            raw_response = requests.post(url, files=files)
        response = json.loads(raw_response.content.decode('utf-8'))
                                
        # Make sure the server did not return an error
        reply = response.get("photo", "No field named 'photo' in the response")
        if reply != "":
            log("ERROR! The server replied with an error.")
            log("The server replied:")
            print(raw_response.content.decode('utf-8'))  
            log("The error is: " + reply)
            raise ValueError(reply)
            
        log("Pictures uploaded successfully.")
        
    except Exception as e:
        log("ERROR! Something happened uploading the pictures!")
        traceback.print_exc()
        log("WARNING: the image was probably not sent!")
        raise e



if "__main__" == __name__:
    main()

