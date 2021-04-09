from typing import Dict

import os
import logging
from flask import Flask, render_template, request, abort, send_from_directory, redirect, url_for

from web_ui.utils import get_version, read_setup_data_file, read_flag_file, _read_data_file, read_dataset_file, clear_logs
from constants import *





def home(feedback: str=None, feedback_sheet_name: str=None, feedback_type: str=None):
    """ The initial page with the forms """

    wifi_data = read_setup_data_file(WIFI_DATA)
    server_data = read_setup_data_file(CONFIGURATION_FILE).get('server', {})
    hotspot_value = read_flag_file(HOTSPOT_FLAG, "ON")

    return render_template("home.html", 
                                title="Setup Iniziale", 
                                version=get_version(),
                                wifi_data=wifi_data, 
                                server_data=server_data, 
                                hotspot_value=hotspot_value,
                                feedback=feedback, 
                                feedback_sheet_name=feedback_sheet_name, 
                                feedback_type=feedback_type)


def webcam():
    """ The page where a picture can be shoot """

    clear_logs(PICTURE_LOGS)  # To not see old logs in the textarea
    return render_template("picture-preview.html", 
                           title="Setup Webcam", 
                           version=get_version(),
                           preview_url=PREVIEW_PICTURE_URL)
