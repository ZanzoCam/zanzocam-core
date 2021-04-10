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
from webcam.errors import UnexpectedServerResponse


class HttpServer:
    """
    Handles all communication with the server over an HTTP connection.
    """
    def __init__(self, parameters: Dict[str, str]):
        # URL is necessary
        self.url = parameters.get("url")
        if not self.url:
            log_error("Cannot contact the server: no server URL found in "
                      "the configuration",
                      fatal="Exiting")
            raise ValueError("No server URL is available")

        self.endpoint = f"{self.url}"
        self.max_photos = parameters.get("max_photos", 0)

        self.credentials = None
        if "username" in parameters.keys():
            self.username = parameters.get("username")
            self.password = parameters.get("password", None)
            self.credentials = requests.auth.HTTPBasicAuth(self.username, self.password)

    @staticmethod
    def _try_print_response_content(response):
        """
        Useful for a tidier logging of responses in case of exceptions
        """
        try:
            return vars(response)
        except Exception:
            return response

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
                raise UnexpectedServerResponse(
                        f"The server did not reply with the "
                        f"expected data. It replied:\n\n{vars(raw_response)}\n")

            log("New configuration downloaded.")
            return response["configuration"]

        except json.decoder.JSONDecodeError as e:
            raise UnexpectedServerResponse(f"The server did not reply valid JSON. "
                                           f"It replied:\n\n{self._try_print_response_content(raw_response)}\n")

        except Exception as e:
            log_error("Something went wrong downloading the new configuration "+
                      f"file from the server. It replied:\n\n{self._try_print_response_content(raw_response)}\n", e)
            raise e


    def download_overlay_image(self, image_name: str) -> None:
        """ 
        Download an overlay image.
        """
        # NOTE: Errors here must escalate
        overlays_url = self.url + ("" if self.url.endswith("/") else "/") + REMOTE_IMAGES_PATH
        # Download from the server
        r = requests.get(f"{overlays_url}{image_name}",
                            stream=True,
                            auth=self.credentials,
                            timeout=REQUEST_TIMEOUT)
        # Save image to file
        if r.status_code == 200:
            r.raw.decode_content = True
            with open(IMAGE_OVERLAYS_PATH / image_name ,'wb') as f:
                shutil.copyfileobj(r.raw, f)
            log(f"New overlay image downloaded: {image_name}")

        # Report every other status code as a failed download
        else:
            log_error(f"New overlay image failed to download: {image_name}")
            log(f"Response status code: {r.status_code}")
            raise ValueError(f"Overlay image failed to download: {image_name}")


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
                      "No logs can be sent. This error will be ignored", e)
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

        try:
            response = raw_response.json()
        except json.decoder.JSONDecodeError as e:
            raise UnexpectedServerResponse(f"The server did not reply valid JSON. "
                                           f"It replied:\n\n{self._try_print_response_content(raw_response)}\n")

        # Make sure the server did not return an error
        reply = response.get("logs", "No field named 'logs' in the response")

        if reply != "" and reply != "Logs not detected":
            log_error("The server replied with an error")
            log(f"The server replied:\n\n{self._try_print_response_content(raw_response)}\n")  
            log(f"The error is {str(reply)}")
            raise ValueError(str(reply))


    def upload_picture(self, image_path: Path, image_name: str, image_extension: str) -> None:
        """
        Uploads the new picture to the server.
        """
        # Deal only with the date-time if max_photos = 0, otherwise rename and send.
        # The server will take care of numbering them if needed
        date_time = datetime.datetime.now().strftime("_%Y-%m-%d_%H:%M:%S") if not self.max_photos else ""
        final_image_path = image_path.parent / (image_name + date_time + "." + image_extension)
        os.rename(image_path, final_image_path)

        # Upload the picture
        files = {'photo': open(final_image_path, 'rb')}
        raw_response = requests.post(self.url, 
                                     files=files, 
                                     auth=self.credentials,
                                     timeout=REQUEST_TIMEOUT)
        try:
            response = raw_response.json()
        except JSONDecodeError as e:
            log_error("An error occurred decoding the JSON: something is probably "+
                      f"wrong with the server's code. The reply is:\n\n{self._try_print_response_content(raw_response)}\n")
            raise UnexpectedServerResponse(e)  # Remember, errors must escalate here

        # Make sure the server did not return an error
        reply = response.get("photo", "< no field named 'photo' in the response >")
        if reply != "":
            log_error("The server replied with an error")
            log(f"The server replied:\n\n{self._try_print_response_content(raw_response)}\n")
            log(f"The error is: {str(reply)}")
            log("WARNING: the image was probably not sent!")
            raise UnexpectedServerResponse(str(reply))  # Remember, errors must escalate here

        return final_image_path
