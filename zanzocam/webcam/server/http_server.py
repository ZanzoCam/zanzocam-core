from typing import Any, List, Dict, Optional

import os
import json
import shutil
import datetime
import requests
from ftplib import FTP, FTP_TLS, error_perm
from json import JSONDecodeError

from constants import *
from webcam.utils import log, log_error, AllStringEncoder
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
            raise ValueError("Cannot contact the server: "
                "no server URL found in the configuration.")

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
            return json.dumps(vars(response), indent=4, cls=AllStringEncoder)
        except Exception as e:
            return str(response)

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
                    f"The server did not reply with a configuration file. "
                    f"Full server response:\n\n"
                    f"{self._try_print_response_content(raw_response)}")

            return response["configuration"]

        except json.decoder.JSONDecodeError as e:
            e.args = (f"The server did not reply valid JSON. "
                      f"JSON exception: {str(e.args[0])}\n"
                      f"Full server response:\n\n"
                      f"{self._try_print_response_content(raw_response)}", )
            raise e.with_traceback(e.__traceback__)

        except Exception as e:
            raise RuntimeError(
                      f"Something went wrong downloading the new configuration "+
                      f"file from the server. The server replied:\n\n"
                      f"{self._try_print_response_content(raw_response)}") from e


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
        if r.status_code < 400:
            r.raw.decode_content = True

            with open(IMAGE_OVERLAYS_PATH / image_name ,'wb') as f:
                shutil.copyfileobj(r.raw, f)
            log(f"New overlay image downloaded: {image_name}")

        # Report every other status code as a failed download
        else:
            raise ValueError(f"Overlay image failed to download: {image_name} "
                             f"Response status code: {r.status_code}")


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
            raise OSError("Something went wrong opening the logs file."
                          "No logs can be sent.") from e
            
        # Prevent the server from returning 'No logs detected' when the file is empty
        if logs == "":
            logs = " ==> No logs found!! <== "
            
        # Send the logs
        data = {'logs': logs}
        raw_response = requests.post(self.url, 
                                     data=data, 
                                     auth=self.credentials, 
                                     timeout=REQUEST_TIMEOUT)

        if raw_response.status_code >= 400:
            raise UnexpectedServerResponse(
                f"The server replied with status code {raw_response.status_code}. "
                f"Check your server configuration for errors. "
                f"Full server response:\n\n"
                f"{self._try_print_response_content(raw_response)}")
        try:
            response = raw_response.json()
        except json.decoder.JSONDecodeError as e:
            e.args = (f"The server did not reply valid JSON. "
                      f"JSON exception: {str(e.args[0])}\n"
                      f"Full server response:\n\n"
                      f"{self._try_print_response_content(raw_response)}", )
            raise e.with_traceback(e.__traceback__)

        # Make sure the server did not return an error
        reply = response.get("logs", "No field named 'logs' in the response")

        if reply != "" and reply != "Logs not detected":
            raise UnexpectedServerResponse(
                f"The server reply was unexpected. "
                f"The reply message is: {str(reply)}\n" 
                f"Full server response:\n\n"
                f"{self._try_print_response_content(raw_response)}")


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

        if raw_response.status_code >= 400:
            raise UnexpectedServerResponse(
                f"The server replied with status code {raw_response.status_code}. "
                f"Check your server configuration for errors. "
                f"Full server response:\n\n"
                f"{self._try_print_response_content(raw_response)}")
        try:
            response = raw_response.json()
        except json.decoder.JSONDecodeError as e:
            e.args = (f"The server did not reply valid JSON. "
                      f"JSON exception: {str(e.args[0])}\n"
                      f"Full server response:\n\n"
                      f"{self._try_print_response_content(raw_response)}", )
            raise e.with_traceback(e.__traceback__)
                    
        # Make sure the server did not return an error
        reply = response.get("photo", "< no field named 'photo' in the response >")
        if reply != "":
            raise UnexpectedServerResponse(
                f"The server reply was unexpected: the image was probably not sent. "
                f"The reply is: {str(reply)}\n" 
                f"Full server response:\n\n" 
                f"{self._try_print_response_content(raw_response)}")

        return final_image_path
