from typing import Dict

import os
import shutil
import picamera
import subprocess
from flask import send_from_directory, abort, flash

from zanzocam.web_ui.utils import read_log_file, write_json_file, write_text_file, toggle_flag, send_from_path, clear_logs
from zanzocam.constants import *



def configure_network(form_data: Dict[str, str]):
    """ 
    Save the network data, write wpa_supplicant.conf 
    and run the hotspot script if necessary.
    """
    # Gather network data
    network_type = form_data.get("network_type", "WiFi").lower()

    if network_type == "wifi":
        config = {
                "type": "WiFi",
                "ssid": form_data.get("network_ssid", None),
                "password": form_data.get("network_password", None)
            }
    elif network_type == "ethernet":
        config = {
                "type": "Ethernet"
            }
    elif network_type == "sim":
        config = {
                "type": "SIM",
                "apn": form_data.get("network_apn", None)
            }
    
    # Save network data
    write_json_file(path=NETWORK_DATA, content=config)
    
    # If the network is a WiFi network, 
    # save the wpa_supplicant file and run the hotspot
    if network_type == "wifi":
        _configure_wifi(config['ssid'], config['password'])

    elif network_type == "sim":
        _configure_modem(config['apn'])
        

def _configure_wifi(ssid, password):
    # Write wpa_supplicant.conf
    write_text_file(path=".tmp-wpa_supplicant",
                    content=f"""
                            ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
                            update_config=1

                            network={{
                                ssid="{ssid}"
                                psk="{password}"
                            }}
                            """)
    # Move wpa_supplicant.conf to its directory
    create_wpa_conf = subprocess.run(
        [
            "/usr/bin/sudo",
            "mv",
            ".tmp-wpa_supplicant",
            "/etc/wpa_supplicant/wpa_supplicant.conf"
        ])
    # Run the autohotspot script
    try:
        autohotspot = subprocess.Popen(["/usr/bin/autohotspot"])
    except subprocess.CalledProcessError as e:
        return f"Si e' verificato un errore: {e}"
    return ""


def _configure_modem(apn):
    pass


def configure_server(form_data: Dict[str, str]):
    """ 
    Save the server data as a minimal configuration.json to bootstrap the webcam
    """
    # Assemble a minimal configuration.json to bootstrap the webcam
    if form_data['server_protocol'] == "FTP":
        webcam_minimal_conf = {
            "server": {
                "protocol": form_data['server_protocol'],
                "username": form_data['server_username'],
                "password": form_data['server_password'],
                "hostname": form_data["server_hostname"],
                "subfolder": form_data.get("server_subfolder"),
                "tls": form_data.get("server_tls", False),
            }
        }
    else:
        webcam_minimal_conf = { 
            "server": {
                "protocol": form_data['server_protocol'],
                "username": form_data['server_username'],
                "password": form_data['server_password'],
                "url": form_data["server_url"],
            }
        }
    # Save the initial configuration file
    try:
        write_json_file(path=CONFIGURATION_FILE, content=webcam_minimal_conf)
        
        if not os.path.exists(CONFIGURATION_FILE + ".bak"):
            write_json_file(path=CONFIGURATION_FILE + ".bak",
                            content=webcam_minimal_conf)
    except Exception as e:
        return f"Si e' verificato un errore nel salvare i dati del server: {e}"
    return ""


def toggle_hotspot(value: str) -> str:
    """ 
    Allow the initial hotspot to turn on in case no known wifi network is detected.
    """
    value = value.upper().strip()
    if value == "YES" or value == "NO":
        return "", toggle_flag(HOTSPOT_FLAG, value)
    abort(404)
    

def toggle_send_logs(value: str) -> str:
    """ 
    Send the logs to the server or not
    """
    value = value.upper().strip()
    if value == "YES" or value == "NO":
        return "", toggle_flag(SEND_LOGS_FLAG, value)
    abort(404)
    

def get_logs(kind: str, filename: str):
    """ 
    Endpoint for fetching the latest logs 
    """
    # Validate the log name
    if filename.lower() == "picture":
        path = PICTURE_LOGS
    else:
        path = CAMERA_LOGS / filename
        if not os.path.isfile(path):
            raise ValueError(f"'{filename}' not found under '{CAMERA_LOG}'.")

    # Return the log as a JSON file
    if kind == "json":
        logs = {"content": ""}
        try:
            logs["content"] = read_log_file(path)
        except FileNotFoundError:
            with open(path, "w"):
                pass
        return logs, 200

    # Return the log as a text file
    elif kind == "text":
        if not os.path.exists(path):
            with open(path, "w"):
                pass
        return send_from_path(path)
    else:
        return f"Logs type {kind} not understood", 500


def get_all_logs():
    """ 
    Endpoint for fetching all the logs as a zip file
    """
    tmp_dir = "/tmp/camera_logs"
    if not os.path.isdir(tmp_dir):
        os.mkdir(tmp_dir)
    
    for file in os.listdir(CAMERA_LOGS):
        if "logs" in str(file):
            shutil.copy2(CAMERA_LOGS / file, tmp_dir)

    zip_name = shutil.make_archive(base_name="/tmp/zanzocam-logs", format="zip", root_dir=tmp_dir)
    return send_from_path(zip_name)


def get_preview():
    """
    Makes a new preview with raspistill and returns the new image.
    """
    with picamera.PiCamera() as camera:
        camera.resolution = (640, 480)
        camera.capture(str(PREVIEW_PICTURE))
    return send_from_path(PREVIEW_PICTURE)


def shoot_picture():
    """ 
    Launches a full ZANZOCAM run manually, to bootstrap the cycle.
    Returns the statuscode to return to the client.
    """
    clear_logs(PICTURE_LOGS)
    try:
        with open(PICTURE_LOGS, 'w') as l:                
            shoot_proc = subprocess.run([ZANZOCAM_EXECUTABLE], stdout=l, stderr=l)
            
    except subprocess.CalledProcessError as e:
        with open(PICTURE_LOGS, 'a') as l:
            l.writelines(f"Si e' verificato un errore: {e}")
        return 500
    return 200


def reboot():
    """ 
    Restarts the ZANZOCAM.
    """
    try:
        reboot = subprocess.run(['/usr/bin/sudo', 'reboot'])
    except subprocess.CalledProcessError as e:
        flash(str(e))
        return 500
    return 200

