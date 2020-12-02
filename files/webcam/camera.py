#!/usr/bin/python3

import os
import math
import json
import time
import shutil
import requests
import datetime
import textwrap
from pathlib import Path
from picamera import PiCamera
from PIL import Image, ImageFont, ImageDraw


path = Path(__file__).parent


def shoot_picture(image_conf):
    """ 
    Shoots the picture.
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
        log("ERROR! Something unexpected happened while generating the overlay. This overlay will be skipped.")
        log("Exception: " + str(e))
        return None        


def _prepare_image_overlay(conf):
    """ 
    Prepares an overlay containing an image.
    Might return None in case of issues. 
    """
    picture_name = conf.get("path")

    if not picture_name:
        log(f"ERROR! This image overlay does not contain the image path. "
        "This overlay will be skipped.")
        return None

    try:
        picture = Image.open(path / picture_name)
    except Exception as e:
        log(f"ERROR! Image '{picture_name}' not found. "
        "This overlay will be skipped.")
        log("Exception: " + str(e))
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
        log("ERROR! Something unexpected happened while generating the overlay. This overlay will be skipped.")
        log("Exception: " + str(e))
        return None      


def process_picture(raw_picture_name, image_conf, overlays_conf):
    """ 
    Renders text and images over the picture and saves the resulting image
    with the proper name and format.
    """
    # Open and measures the picture
    picture = Image.open(raw_picture_name)
    picture_size = picture.size

    # Creates the components to overlay
    pieces_to_layout = []
    for piece_position, piece_conf in overlays_conf.items():
    
        kind = piece_conf.get("type", "missing")
        if kind == "text":
            overlay = _prepare_text_overlay(piece_conf, picture_size)
            if overlay is not None:
                pieces_to_layout.append((piece_position, piece_conf, overlay))

        elif kind == "image":
            overlay = _prepare_image_overlay(piece_conf)
            if overlay is not None:
                pieces_to_layout.append((piece_position, piece_conf, overlay))
        
        elif kind == "missing":
            log(f"ERROR! Missing overlay name! This overlay will be skipped.")
        else:
            log(f"ERROR! Overlay name '{kind}' not recognized. Valid names: "
            "text, image. This overlay will be skipped.")

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
    image_extension = image_conf.get("extension", "png")
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
        log("The error is: " + str(e))
        raise e
        
        
def send_logs(url, user=None, pwd=None):
    """ 
    Send the logs to the server. 
    Tries to never fail in order not to break the main routine if something 
    goes wrong at this stage (even though it's a worrying sign).
    """
    log(f"Uploading logs to {url}")
        
    # Load the logs content
    try:
        logs = " ==> No logs found!! <== "
        with open(path/"logs.txt", "r+") as l:
            logs = l.readlines()
    except Exception as e:
        log("ERROR! Something happened opening the logs file.")
        log("The exception is " + str(e))
        log("This error will be ignored.")
        return
                
    # Prepare and send the request
    try:
        data = {'logs': logs}
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
            print(response.content.decode('utf-8'))  
            log("The error is " + reply)
            log("This error will be ignored.")
            return
            
        log("Logs uploaded successfully.")
    
    except Exception as e:
        log("ERROR! Something happened uploading the logs file.")
        log("The exception is " + str(e))
        log("This error will be ignored.")
        return


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
        
        print(user, pwd)
                
        # Backup the old config file
        shutil.copy(path / "configuration.json", path / "configuration.prev.json")

    except Exception as e:
        log("ERROR! Something went wrong loading the old configuration file.")
        log("Exception is:" + str(e))
        log("This error is not recoverable. Exiting.")
        return None
    
    try:
        # Fetch the new config
        if user:
            response = requests.get(url, auth=requests.auth.HTTPBasicAuth(user, pwd))
        else:
            response = requests.get(url)

        # Write the new config into the configuration file                    
        response_dict = json.loads(response.content.decode('utf-8'))
        new_config = response_dict["configuration"]
        
        with open(path / "configuration.json", 'w') as c:
            json.dump(new_config, c, indent=4)

        log("Configuration downloaded successfully:")
        print(json.dumps(new_config, indent=4))
        
        ################################################
        # TODO Apply new system configs like crontab etc...
        ################################################

        # Return the downloaded data
        return new_config
        
    except Exception as e:
        log("ERROR! Something went wrong fetching the new config file from the server.")
        log("The exception is:" + str(e))
        log("The server replied:")
        print(response.content.decode('utf-8'))  
        log("Falling back to old configuration file.") 
        return old_conf         
    

def main_procedure(conf, retrying=False):
    try:
        # Send logs of the previous run
        server_url = conf.get("server_url")
        server_user = conf.get("server_username")
        server_pwd = conf.get("server_password")
        send_logs(server_url, server_user, server_pwd)
        
        # Shoot picture
        log("Taking photo")
        raw_pic_name = shoot_picture(conf.get("image", {}))
        
        # Add overlays
        log("Rendering photo")
        final_pic_name = process_picture(raw_pic_name, conf.get("image", {}), conf.get("overlays", {}))
        
        # Upload picture
        log("Uploading photo")
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
            log("The exception is: " + str(e))
            log("+++++++++++++++++++++++++++++++++++++++++++")
            log("Discarding newest configuration and restoring the previous values.")
            
            shutil.copy(path / "configuration.prev.json", path / "configuration.json")
            conf = {}
            with open(path / "configuration.json", 'r') as c:
                conf = json.load(c)
            
            main_procedure(conf, retrying=True)
            log("+++++++++++++++++++++++++++++++++++++++++++")
            return 
            
        # That's the second run that failed: give up.
        log("ERROR! Something happened while running with the old configuration file too!")
        log("The exception is: " + str(e))
        log("Can't fix the issue any further: giving up.")
        return
        

def log(msg):
    print(f"{datetime.datetime.now()} -> {msg}")
        

def main():
    log("Start")
    conf = get_configuration()
    if conf is not None:
        main_procedure(conf)
    print("\n==========================================\n")
    
    
    

if "__main__" == __name__:
    main()


