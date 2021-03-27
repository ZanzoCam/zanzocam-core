from typing import Dict

import os
import logging
from flask import Flask, render_template, request, abort, send_from_directory, redirect, url_for

#from web_ui import low_light
from web_ui.utils import read_setup_data_file, read_flag_file, _read_data_file, read_dataset_file, clear_logs
from constants import *



def home(feedback: str=None, feedback_sheet_name: str=None, feedback_type: str=None):
    """ The initial page with the forms """

    wifi_data = read_setup_data_file(WIFI_DATA)
    server_data = read_setup_data_file(CONFIGURATION_FILE).get('server', {})
    hotspot_value = read_flag_file(HOTSPOT_FLAG, "ON")

    return render_template("home.html", 
                                title="Setup Iniziale", 
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
                           preview_url=PREVIEW_PICTURE_URL)


def low_light_calibration():
    """ The page where to see and set the low-light calibration parameters """

    # If the file does not exist, create it
    if not os.path.exists(CALIBRATION_DATASET):
        with open(CALIBRATION_DATASET, 'w') as calib:
            pass

    # Read the calibration flag
    calibration_flag = read_flag_file(CALIBRATION_FLAG, "OFF")

    # Read old a and b values
    old_a_value, old_b_value = _read_data_file(CALIBRATED_PARAMS, default="0,0", action=lambda d: d.read().strip(), catch_errors=True).split(",")

    # Read the values as strings for editing and make sure there are enough values
    calibration_data = []
    if os.path.exists(CALIBRATION_GRAPH):
        os.remove(CALIBRATION_GRAPH)  # To avoid seeing a stale one if something goes wrong

    try:
        calibration_data = read_dataset_file(CALIBRATION_DATASET)
        calibration_data.sort()
        calibration_data = "".join([line.strip()+"\n" for line in calibration_data if line.strip() != ""])
    
        if len(calibration_data) < 10:
            raise ValueError("Non hai raccolto abbastanza dati per effettuare la calibrazione (minimo 10 valori).")

        # Compute the new values and plot the data
        a_value, b_value = low_light.calculate_parameters()
        low_light.plot_curve_fit(a_value, b_value, int(old_a_value), int(old_b_value))

        return render_template("low-light-calibration.html", 
                        title="Calibrazione Webcam",
                        calibration_flag=calibration_flag,
                        figure=CALIBRATION_GRAPH_URL,
                        calibration_data=calibration_data,
                        old_a_value=old_a_value,
                        old_b_value=old_b_value,
                        a_value=a_value,
                        b_value=b_value)

    except ValueError as e:
        return render_template("low-light-calibration.html",
                            calibration_flag=calibration_flag,
                            title="Calibrazione Webcam",
                            figure=CALIBRATION_GRAPH_URL,
                            calibration_data=calibration_data,
                            feedback=str(e))

    except Exception as ee:
        logging.error(ee)
        return render_template("low-light-calibration.html", 
                        title="Calibrazione Webcam",
                        calibration_data=calibration_data,
                        calibration_flag=calibration_flag,
                        figure=CALIBRATION_GRAPH_URL,
                        feedback="Qualcosa e' andato storto calcolando la curva. Verifica i dati inseriti e correggili se necessario.")
