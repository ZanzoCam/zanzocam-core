from typing import Any, List, Dict, Optional

import os
import json
import shutil
import datetime
import requests
from ftplib import FTP, FTP_TLS

from webcam.constants import *
from webcam.utils import log, log_error
from webcam.configuration import Configuration



class Server:
    """
    Handles all communication with the server.
    """
    def __init__(self, parameters: Dict[str, str]):
    
        self.protocol = parameters.get("protocol")
        if not self.protocol:
            log_error("The communication protocol with the server (HTTP, FTP) "+
                      "was not specified.", 
                      fatal="Cannot communicate with the server. Exiting")
            raise ValueError("No protocol is available to estabilish a "
                             "connection to the server.")
                             
        elif self.protocol.upper() == "HTTP":
            self._server = _HttpServer(parameters)
            
        elif self.protocol.upper() == "FTP":
            self._server = _FtpServer(parameters)


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

            log("Configuration updated successfully.")
            return configuration

        except Exception as e:
            log_error("Something went wrong fetching the new config file from the server.", e)
            raise e


    def download_overlay_images(self, images_list: List[str]) -> None:
        """ 
        Download all the overlay images that should be re-downloaded.
        If it fails, logs it and replaces that image with a transparent pixel, 
        to avoid adding checks later in the processing.
        """
        log(f"Downloading overlay images fron {self._server.endpoint} into {IMAGE_OVERLAYS_PATH}")
        log(f"Images to download: {images_list}")

        for image_name in images_list:
            try:
                # Download image from the server
                self._server.download_overlay_image(image_name)
                
            except Exception as e:
                # Replace with transparent pixel if it failed.
                log_error(f"New overlay image failed to download: {image_name}")
                log("Replacing it with a transparent pixel.")
                shutil.copy2(
                    IMAGE_OVERLAYS_PATH / "fallback-pixel.png", 
                    IMAGE_OVERLAYS_PATH / image_name)


    def upload_logs(self, path: Path = LOGS_PATH):
        """ 
        Send the logs to the server.
        """
        # NOTE: exceptions in here should NOT escalate. Catch everything!!
        log(f"Uploading logs to {self._server.endpoint}")
        # Send the logs
        try:
            self._server.send_logs(path)
            log("Logs uploaded successfully.")
            # Clear the logs once they have been uploaded
            with open(path, "w") as l:
                pass        
        except Exception as e:
            log_error("Something happened while uploading the logs file. "
                      "This error will be ignored.", e)
            return


    def upload_picture(self, image_name: str) -> None:
        """
        Uploads the new picture to the server.
        """
        # Do NOT escalate errors from here: catch everything
        log(f"Uploading picture to {self._server.endpoint}")
        try:
            # Upload the picture
            self._server.upload_picture(image_name)
            log("Pictures uploaded successfully.")
                        
        except Exception as e:
            log_error("Something happened uploading the pictures!", e)
            log("WARNING: the image was probably not sent!")



################################################################################

class _HttpServer:
    """
    Handles all communication with the server over an HTTP connection.
    """
    def __init__(self, parameters: Dict[str, str]):
        # URL is necessary
        self.url = parameters.get("url")
        if not self.url:
            log_error("Cannot contact the server: no server URL found in "
                      "the configuration.",
                      fatal="Exiting.")
            raise ValueError("No server URL is available.")

        self.endpoint = f"{self.url}"

        self.credentials = None
        if "username" in parameters.keys():
            self.username = parameters.get("username")
            self.password = parameters.get("password", None)
            self.credentials = requests.auth.HTTPBasicAuth(self.username, self.password)


    def download_new_configuration(self) -> Dict[str, Any]:
        """
        Download the new configuration file from the server.
        """
        # NOTE: Errors here must escalate
        raw_response = {}
        try:
            # Fetch the new config
            auth = None
            raw_response = requests.get(self.url, auth=self.credentials, timeout=REQUEST_TIMEOUT)
            response = raw_response.json()

            if "configuration" not in response:
                raise ValueError("The server did not reply with the expected data.")

            log("New configuration downloaded.")
            return response["configuration"]

        except Exception as e:
            log_error("Something went wrong downloading the new configuration "+
                      "file from the server.", e)
            log("The server replied:")
            print(vars(raw_response))
            raise e


    def download_overlay_image(self, image_name: str) -> None:
        """ 
        Download an overlay image.
        """
        # NOTE: Errors here must escalate
        overlays_url = self.url + ("" if self.url.endswith("/") else "/") + REMOTE_IMAGES_PATH
        for image in images_list:
            # Download from the server
            r = requests.get(f"{overlays_url}{image}",
                                stream=True,
                                auth=self.credentials,
                                timeout=REQUEST_TIMEOUT)
            # Save image to file
            if r.status_code == 200:
                r.raw.decode_content = True
                with open(IMAGE_OVERLAYS_PATH / image ,'wb') as f:
                    shutil.copyfileobj(r.raw, f)
                log(f"New overlay image downloaded: {image}")

            # Report every other status code as a failed download
            else:
                log_error(f"New overlay image failed to download: {image}")
                log(f"Response status code: {r.status_code}")
                raise ValueError("Overlay image failed to download: {image}")


    def send_logs(self, path: Path):
        """ 
        Send the logs to the server.
        """
        # NOTE: Errors here must escalate
        logs = ""
        # Load the logs from file
        try:
            if os.path.exists(path):
                with open(path, "r") as l:
                    logs = l.readlines()
                    logs = "".join(logs)
        except Exception as e:
            log_error("Something went wrong opening the logs file."
                      "No logs can be sent. This error will be ignored.", e)
            raise e
            
        # Prevent the server from returning 'No logs detected' when the file is empty
        if logs == "":
            logs = " ==> No logs found!! <== "
            
        # Send the logs
        data = {'logs': logs}
        raw_response = requests.post(self.url, 
                                     data=data, 
                                     auth=self.credentials, 
                                     timeout=REQUEST_TIMEOUT)
        response = raw_response.json()
        
        # Make sure the server did not return an error
        reply = response.get("logs", "No field named 'logs' in the response")
        if reply != "":
            log_error("The server replied with an error.")
            log("The server replied:")
            log(vars(raw_response))  
            log("The error is " + str(reply))
            raise ValueError("The server replied with:" + str(reply))


    def upload_picture(self, image_name: str) -> None:
        """
        Uploads the new picture to the server.
        """
        # NOTE: Errors from here must escalate
        if not image_name:
            log("Cannot upload the picture: picture location not given", 
                fatal="Picture won't be uploaded.")        

        # Upload the picture
        files = {'photo': open(image_name, 'rb')}
        raw_response = requests.post(self.url, 
                                     files=files, 
                                     auth=self.credentials,
                                     timeout=REQUEST_TIMEOUT)
        response = raw_response.json()
                                
        # Make sure the server did not return an error
        reply = response.get("photo", "No field named 'photo' in the response")
        if reply != "":
            log_error("The server replied with an error.")
            log("The server replied:")
            print(raw_response.text())
            log("The error is: " + reply)
            log("WARNING: the image was probably not sent!")
            return


################################################################################

class _FtpServer:
    """
    Handles all communication with the server over an FTP connection.
    """
    def __init__(self, parameters: Dict[str, str]):
        # host is necessary
        self.hostname = parameters.get("hostname")
        if not self.hostname:
            log_error("Cannot contact the server: no hostname found in "
                      "the configuration.",
                      fatal="Exiting.")
            raise ValueError("No hostname is available.")

        # username is necessary
        self.username = parameters.get("username")
        if not self.username:
            log_error("Cannot contact the server: no username found in "
                      "the configuration.",
                      fatal="Exiting.")
            raise ValueError("No username is available.")

        # password can be blank  (TODO really it can? Check)
        self.password = parameters.get("password", "")
        self.endpoint = f"ftp://{self.username}@{self.hostname}"
        self.no_tls = parameters.get("not_tls", False)
        # self.use_sftp = parameters.get("sftp", False)  # TODO can we support SFTP easily?
        
        # Estabilish the FTP connection
        try:
            if self.no_tls:
                self._ftp_client = FTP(host=self.hostname, 
                                        user=self.username, 
                                        passwd=self.password, 
                                        timeout=REQUEST_TIMEOUT*2)
            else:
                self._ftp_client = FTP_TLS(host=self.hostname, 
                                            user=self.username, 
                                            passwd=self.password, 
                                            timeout=REQUEST_TIMEOUT*2)
                self._ftp_client.prot_p()  # Set up secure data connection.
                
            self._ftp_client.cwd('zanzocam')
        except Exception as e:
            log_error("Failed to estabilish a connection with the FTP server", e,
                      fatal="Exiting.")
        

    def download_new_configuration(self) -> Dict[str, Any]:
        """
        Download the new configuration file from the server.
        """
        # NOTE: Errors here can escalate
        
        self.configuration_string = ""
        # Callback for the incoming data
        def store_line(line):
            self.configuration_string += line

        # Fetch the new config
        response = self._ftp_client.retrlines("RETR config/configuration.json", store_line)

        # Make sure the server did not reply with an error
        if "226" in response:
            log("New configuration downloaded.")
            configuration_data = json.loads(self.configuration_string)
            self.configuration_string = ""
            return configuration_data
            
        raise ValueError("The server replied with an error code: " + response)
            

    def download_overlay_image(self, image_name: str) -> None:
        """ 
        Download an overlay image.
        """
        # NOTE: Errors here can escalate
        with open(IMAGE_OVERLAYS_PATH / image_name ,'wb') as overlay:
            response = self._ftp_client.retrbinary(
                            f"RETR config/overlays/{image_name}", overlay.write)
        if not "226" in response:
            raise ValueError(f"The server replied with an error code for {image_name}: " + response)
        log(f"New overlay image downloaded: {image_name}")
        

    def send_logs(self, path: Path):
        """ 
        Send the logs to the server.
        """
        # NOTE: exceptions in here must escalate.
        
        # Make sure the file in question exists and has some content
        if not os.path.exists(path):
            with open(path, "r") as l:
                l.writelines(" ==> No logs found!! <==")
        
        # Fetch the new overlay
        with open(path ,'rb') as logs:
            response = self._ftp_client.storlines(
                f"STOR logs/logs_{datetime.datetime.now()}.txt", logs)
                
        # Make sure the server did not reply with an error
        if not "226" in response:
            raise ValueError(f"The server replied with an error code while " +
                            "uploading the logs: " + response)


    def upload_picture(self, image_name: str) -> None:
        """
        Uploads the new picture to the server.
        """
        # NOTE: Errors from here must escalate
        if not image_name:
            log("Cannot upload the picture: picture location not given", 
                fatal="Picture won't be uploaded.")
        
        # Make sure the file in question exists
        if not os.path.exists(image_name):
            log(f"Cannot upload the picture: image file {image_name} does not exist!", 
                fatal="Picture won't be uploaded.")
            raise ValueError(f"Picture file {image_name} does not exist")
        
        # Fetch the new overlay
        with open(image_name ,"rb") as image:
            response = self._ftp_client.storbinary(
                f"STOR pictures/{image_name}", image)
                
        # Make sure the server did not reply with an error
        if not "226" in response:
            log_error(f"The server replied with an error code while " +
                            "uploading the picture: " + response)
            log("WARNING: the image was probably not sent!")
            raise ValueError(f"Failed to upload the picture")

