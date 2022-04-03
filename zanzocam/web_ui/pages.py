import os
import datetime
from time import strftime

from flask import render_template

from zanzocam.web_ui.utils import read_setup_data_file, read_flag_file, read_log_file, clear_logs
from zanzocam.constants import *



def home_page():
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

def network_page():
    """ The page with the network forms """
    network_data = read_setup_data_file(NETWORK_DATA)
    return render_template("network.html", 
                            title="Setup Rete", 
                            version=VERSION,
                            network_data=network_data)

def server_page():
    """ The page with the server data forms """
    server_data = read_setup_data_file(CONFIGURATION_FILE).get('server', {})
    return render_template("server.html", 
                            title="Setup Server", 
                            version=VERSION,
                            server_data=server_data)

def webcam_page():
    """ The page where a picture can be shoot """
    clear_logs(PICTURE_LOGS)  # To not see old logs in the textarea
    return render_template("webcam.html", 
                           title="Setup Webcam", 
                           version=VERSION,
                           preview_url=PREVIEW_PICTURE_URL)

def logs_page():
    """ The page with the logs browser """
    logs = {}
    oldest_log_date = None

    if CAMERA_LOGS.is_dir():
        for logfile in os.listdir(CAMERA_LOGS):
            
            logs[Path(logfile).name] = read_log_file(CAMERA_LOGS / logfile)

            edited_time = os.path.getmtime(CAMERA_LOGS / logfile)
            if not oldest_log_date or edited_time < oldest_log_date:
                oldest_log_date = edited_time

        total_logs_size = sum(file.stat().st_size for file in Path(CAMERA_LOGS).rglob('*')) / 1024

    return render_template("logs.html",
                            title="Logs Browser",
                            version=VERSION,
                            logs=logs,
                            logs_count=len(logs.keys()),
                            logs_size=f"{total_logs_size:.2f}",
                            oldest_log=datetime.datetime.strftime(datetime.datetime.fromtimestamp(oldest_log_date), "%d-%m-%Y %H:%M:%S")
            )
