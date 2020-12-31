from typing import List, Dict, Optional

import os
import shutil
import requests

from webcam.constants import *
from webcam.utils import log, log_error
from webcam.configuration import Configuration



class Server:
    """
    Handles all communication with the server.
    """
    def __init__(self, url: str, username: Optional[str], password: Optional[str]):
        # URL is necessary
        if not url:
            log_error("Cannot contact the server: no server URL found in "
                      "the configuration.",
                      fatal="No server data is available, so cannot fetch "
                      "a new configuration file. Exiting.")
            raise ValueError("No server data is available.")

        self.url = url
        self.credentials = None
        if username:
            self.username = username
            self.password = password
            self.credentials = requests.auth.HTTPBasicAuth(username, password)


    def update_configuration(self, old_configuration: Configuration) -> Configuration:
        """
        Download the new configuration file from the server and updates it
        locally.
        """
        # NOTE: Errors here should escalate, so always rethrow them
        raw_response = {}
        try:
            log(f"Downloading the new configuration file from {self.url}")

            # Fetch the new config
            auth = None
            raw_response = requests.get(self.url, auth=self.credentials, timeout=REQUEST_TIMEOUT)
            response = raw_response.json()

            if "configuration" not in response:
                raise ValueError("The server did not reply with the expected data.")

            # If the old server replied something good, it's OK to backup its data.
            old_configuration.backup()

            # Create new configuration object (overwrites configuration.json)
            configuration = Configuration.create_from_dictionary(response["configuration"])

            # Getting new overlays associated with the configuration
            self.download_overlay_images(configuration.images_to_download())

            log("Configuration updated successfully.")
            return configuration

        except Exception as e:
            log_error("Something went wrong fetching the new config file from the server.", e)
            log("The server replied:")
            print(vars(raw_response))
            raise e


    def download_overlay_images(self, images_list: List[str]) -> None:
        """ 
        Download all the overlay images that should be re-downloaded.
        If it fails, logs it and replaces that image with a transparent pixel, 
        to avoid adding checks later in the processing.
        """
        log(f"Downloading overlay images into {IMAGE_OVERLAYS_PATH}")
        log(f"Images to download: {images_list}")
        url = self.url + ("" if self.url.endswith("/") else "/") + REMOTE_IMAGES_PATH

        for image in images_list:
            # Download from the server
            r = requests.get(f"{url}{image}",
                                stream=True,
                                auth=self.credentials,
                                timeout=REQUEST_TIMEOUT)
            # Save image to file
            if r.status_code == 200:
                r.raw.decode_content = True
                with open(IMAGE_OVERLAYS_PATH / image ,'wb') as f:
                    shutil.copyfileobj(r.raw, f)
                log(f"New overlay image downloaded: {image}")

            # Replace with transparent pixel if it failed.
            else:
                log_error(f"New overlay image failed to download: {image}")
                log(f"Response status code: {r.status_code}")
                log("Replacing it with a transparent pixel.")
                shutil.copy2(IMAGE_OVERLAYS_PATH / "fallback-pixel.png", IMAGE_OVERLAYS_PATH / image)


    def upload_logs(self, path: Path = LOGS_PATH):
        """ 
        Send the logs to the server.
        """
        # NOTE: exceptions in here should NOT escalate. Catch everything!!
        log(f"Uploading logs to {self.url}")
            
        # Load the logs content
        logs = " ==> No logs found!! <== "
        try:
            if os.path.exists(path):
                with open(path, "r") as l:
                    logs = l.readlines()
                    logs = "".join(logs)
                    
        except Exception as e:
            log_error("Something happened opening the logs file."
                      "No logs can be sent. This error will be ignored.", e)
            return

        # Prepare and send the request
        data = {'logs': logs}
        try:
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
                log("This error will be ignored.")
                return

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
        if not image_name:
            log("Cannot upload the picture: picture location not given", 
                fatal="Picture won't be uploaded.")
        
        log("Uploading picture")
        try:
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
                
            log("Pictures uploaded successfully.")
            
        except Exception as e:
            log_error("Something happened uploading the pictures!", e)
            log("WARNING: the image was probably not sent!")




