from typing import Any, List, Dict, Optional

import os
import json
import shutil
import datetime
import requests
from ftplib import FTP, FTP_TLS, error_perm
from json import JSONDecodeError

from constants import *
from webcam.utils import log, log_error, log_row
from webcam.configuration import Configuration
from webcam.server.http_server import HttpServer
from webcam.server.ftp_server import FtpServer
from webcam.errors import ServerError, UnexpectedServerResponse



class Server:
    """
    Handles all communications with the server.
    """
    def __init__(self, configuration: 'Configuration'):

        parameters = getattr(configuration, 'server', None)

        if not getattr(configuration, 'server'):
            raise ServerError("No server information found in the configuration file")

        self.protocol = parameters.get("protocol")
        if not self.protocol:
            raise ServerError("The communication protocol with the server (HTTP, FTP) "+
                             "was not specified. No protocol is available to estabilish a "
                             "connection to the server")
                             
        elif self.protocol.upper() == "HTTP":
            self._server = HttpServer(parameters)
            
        elif self.protocol.upper() == "FTP":
            self._server = FtpServer(parameters)

        self.final_image_path = None  # To avoid anyone trying to access an attribute that does not exist

    def update_configuration(self, old_configuration: Configuration) -> Configuration:
        """
        Download the new configuration file from the server and updates it
        locally.
        """
        # NOTE: Errors here should escalate, so always rethrow them
        log(f"Downloading the new configuration file from {self._server.endpoint}")
        try:
            # Get the new configuration from the server
            configuration_data = self._server.download_new_configuration()
            
            # If the old server replied something good, it's OK to backup its data.
            old_configuration.backup()

            # Create new configuration object (overwrites configuration.json)
            configuration = Configuration.create_from_dictionary(configuration_data)

            # Getting new overlays associated with the configuration
            self.download_overlay_images(configuration.images_to_download())

            log("Configuration updated successfully")
            return configuration

        except Exception as e:
            log_error("Something went wrong fetching the new config file from the server", e)
            raise e


    def download_overlay_images(self, images_list: List[str]) -> None:
        """ 
        Download all the overlay images that should be re-downloaded.
        If it fails, logs it and replaces that image with a transparent pixel, 
        to avoid adding checks later in the processing.
        """
        log(f"Downloading overlay images from {self._server.endpoint} into {IMAGE_OVERLAYS_PATH}")
        log(f"Images to download: {images_list}")

        for image_name in images_list:
            if not image_name or image_name == "":
                log_error("This overlay image has no name! Skipping. "+
                          "This is probably an empty 'path' entry in an overlay "+
                          "configuration: please remove it or give it a value!")
                continue
                
            try:
                # Download image from the server
                self._server.download_overlay_image(image_name)
                
            except Exception as e:
                # Replace with transparent pixel if it failed.
                log_error(f"New overlay image failed to download: {image_name}")
                log("Replacing it with a transparent pixel")
                shutil.copy2(
                    IMAGE_OVERLAYS_PATH / "fallback-pixel.png", 
                    IMAGE_OVERLAYS_PATH / image_name)


    def upload_logs(self, path: Path = CAMERA_LOG):
        """ 
        Send the logs to the server.
        """
        # NOTE: exceptions in here should NOT escalate. Catch everything!!
        try:
            self._server.send_logs(path)
            # Clear the logs once they have been uploaded
            with open(path, "w") as l:
                pass
            log(f"Logs uploaded successfully to {self._server.endpoint}")
            
        except Exception as e:
            log_row("-")
            log_error(f"Something happened while uploading the logs file to {self._server.endpoint}. "
                      "This error will be ignored", e)
            log_row("-")
            return
    
    
    def upload_failure_report(self, wrong_conf: Dict[str, Any], 
            right_conf: Dict[str, Any], logs_path: Path = CAMERA_LOG, ) -> None:
        """ 
        Send the logs to the server.
        """
        # NOTE: exceptions in here should NOT escalate. Catch everything!!
        log(f"Sending failure report to {self._server.endpoint}")
        
        logs = ""
        try:
            if os.path.exists(logs_path):
                with open(logs_path, "r") as l:
                    logs = l.read()
        except Exception as e:
            log_error("Something went wrong opening the logs file."
                      "The report will contain no logs. This error will be ignored", e)

        if not logs or logs == "":
            logs = " ==> No logs found!! <== "
        
        with open(FAILURE_REPORT_PATH, "w") as report:
            report.writelines(
                "**********************\n"+
                "*   FAILURE REPORT   *\n"+
                "**********************\n" +
                "Failed to use the server information contained in the new configuration file.\n"+
                "New, NOT working server information is the following:\n"+
                json.dumps(wrong_conf, indent=4) +
                "\nPlease fix the above information in the configuration file "+
                "that is hosted here, or fix the affected server.\n" +
                "ZANZOCAM will keep trying to download a new config with this parameters instead:\n"+
                json.dumps(right_conf, indent=4) +
                "\nHere below is the log of the last run before the crash.\n\n" +
                "**********************\n\n"+
                logs
            )
        # Send the logs
        try:
            self._server.send_logs(FAILURE_REPORT_PATH)
            log("Failure report uploaded successfully")

        except Exception as e:
            log_error("Something happened while uploading the failure report. "
                      "This error will be ignored", e)
            return


    def upload_picture(self, image_path: Path, image_name: str, image_extension: str) -> None:
        """
        Uploads the new picture to the server.
        """
        # Note: Errors here MUST escalate
        
        if not os.path.exists(image_path):
            log(f"No picture to upload: {image_path} does not exist")
            return

        log(f"Uploading picture to {self._server.endpoint}")

        if not image_name or not image_path or not image_extension:
            log(f"Cannot upload the picture: picture name ({image_name}) " +
                f"or location ({image_path}) or extension ({image_extension}) not given", 
                fatal="Picture won't be uploaded")
        
        # Make sure the file in question exists
        if not os.path.exists(image_path):
            log(f"Cannot upload the picture: {image_path} does not exist!", 
                fatal="Picture won't be uploaded")
            raise ValueError(f"Picture file {image_path} does not exist")

        # Upload the picture
        self.final_image_path = self._server.upload_picture(image_path, image_name, image_extension)
        log(f"Picture {self.final_image_path.name} uploaded successfully")
