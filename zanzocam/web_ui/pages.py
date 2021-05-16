from typing import Dict

import os
import logging
from flask import Flask, render_template, request, abort, send_from_directory, redirect, url_for

from web_ui.utils import read_setup_data_file, read_flag_file, _read_data_file, read_dataset_file, clear_logs
from constants import *





def home():
    """ The initial page with the summary """
    hotspot_value = read_flag_file(HOTSPOT_FLAG, "YES")
    network_data = read_setup_data_file(NETWORK_DATA)
    server_data = read_setup_data_file(CONFIGURATION_FILE).get('server', {})
    return render_template("home.html", 
                                title="Setup", 
                                version=VERSION, 
                                hotspot_value=hotspot_value,
                                network_data=network_data,
                                server_data=server_data)

def network():
    """ The page with the network forms """
    network_data = read_setup_data_file(NETWORK_DATA)
    return render_template("network.html", 
                                title="Setup Rete", 
                                version=VERSION,
                                network_data=network_data)

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
