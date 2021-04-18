from typing import Dict

import os
import logging
from flask import Flask, render_template, request, abort, send_from_directory, redirect, url_for

from web_ui.utils import read_setup_data_file, read_flag_file, _read_data_file, read_dataset_file, clear_logs
from constants import *





def home():
    """ The initial page with the summary """
    hotspot_value = read_flag_file(HOTSPOT_FLAG, "ON")
    wifi_data = read_setup_data_file(WIFI_DATA)
    server_data = read_setup_data_file(CONFIGURATION_FILE).get('server', {})
    return render_template("home.html", 
                                title="Setup", 
                                version=VERSION, 
                                hotspot_value=hotspot_value,
                                wifi_data=wifi_data,
                                server_data=server_data)

def wifi():
    """ The page with the wifi forms """
    wifi_data = read_setup_data_file(WIFI_DATA)
    return render_template("wifi.html", 
                                title="Setup WiFi", 
                                version=VERSION,
                                wifi_data=wifi_data)

def server():
    """ The page with the server data forms """
    server_data = read_setup_data_file(CONFIGURATION_FILE).get('server', {})
    return render_template("server.html", 
                                title="Setup Server", 
                                version=VERSION,
                                server_data=server_data)

def webcam():
    """ The page where a picture can be shoot """
    clear_logs(PICTURE_LOGS)  # To not see old logs in the textarea
    return render_template("webcam.html", 
                           title="Setup Webcam", 
                           version=VERSION,
                           preview_url=PREVIEW_PICTURE_URL)
