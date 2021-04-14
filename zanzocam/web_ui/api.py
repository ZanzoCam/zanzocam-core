from typing import Dict

import os
import json
import picamera
import subprocess
from flask import send_from_directory

from web_ui.utils import read_log_file, write_json_file, write_text_file, toggle_flag, send_from_path, clear_logs
from constants import *



def configure_wifi(form_data: Dict[str, str]):
    """ 
    Save the WiFi data, write wpa_supplicant.conf and run the hotspot script.
    """
    # Gather wifi data
    ssid = form_data["wifi_ssid"]
    password = form_data["wifi_password"]

    # Save wifi data
    write_json_file(path=WIFI_DATA, 
                    content={
                        "ssid": ssid,
                        "password": password
                    })
    
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
    except Exception as e:
        return f"Si e' verificato un errore nel salvare i dati del server: {e}"
    return ""


def toggle_hotspot(value) -> int:
    """ 
    Allow the initial hotspot to turn on in case no known wifi network is detected.
    """
    return "", toggle_flag(HOTSPOT_FLAG, value)


def toggle_calibration(value):
    """ 
    Allow ZANZOCAM to take as many pictures as needed in low-light conditions, and
    to save the data obtained in the process for a future calibration step.
    """
    return "", toggle_flag(CALIBRATION_FLAG, value)


def get_logs(kind: str, name: str):
    """ 
    Endpoint for fetching the latest logs 
    """

    # Figure out which log has been requested
    if name == "hotspot":
        logs_path = HOTSPOT_LOGS
    elif name == "picture":
        logs_path = PICTURE_LOGS
    else:
        return f"Logs name {name} not understood", 500

    # Return the log as a JSON file
    if kind == "json":
        logs = {"content": ""}
        try:
            logs["content"] = read_log_file(logs_path)
        except FileNotFoundError:
            with open(logs_path, "w"):
                pass
        return logs, 200

    # Return the log as a text file
    elif kind == "text":
        if not os.path.exists(logs_path):
            with open(logs_path, "w"):
                pass
        return send_from_path(logs_path)
    else:
        return f"Logs type {kind} not understood", 500


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
        return 500
    return 200

