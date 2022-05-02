from typing import Any, Dict

import os
import json
import shutil
import datetime
import requests
import traceback

from zanzocam.constants import *
from zanzocam.webcam.errors import ServerError
from zanzocam.webcam.utils import log, log_error, retry, AllStringEncoder


class HttpServer:
    """
    Handles all communication with the server over an HTTP connection.
    """
    def __init__(self, parameters: Dict[str, str]):
        if not isinstance(parameters, dict):
            raise ValueError("HttpServer can only be instantiated with a dictionary.")

        # URL is necessary
        self.url = parameters.get("url")
        if not self.url:
            raise ServerError("Cannot contact the server: "
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
        r = "[no response from server]"
        try:
            # Fetch the new config
            r = requests.get(self.url, auth=self.credentials, timeout=REQUEST_TIMEOUT)
            
            if r.status_code >= 400:
                raise ServerError(f"Failed to download the configuration file. "
                                  f"The server replied with status code "
                                  f"{r.status_code} ({r.reason}). "
                                  f"Check your server configuration for errors. "
                                  f"Full server response:\n\n"
                                  f"{self._try_print_response_content(r)}")
                
            response = r.json()
            if "configuration" not in response:
                raise ServerError(
                    f"The server did not reply with a configuration file. "
                    f"Full server response:\n\n"
                    f"{self._try_print_response_content(r)}")

            return response["configuration"]

        except json.decoder.JSONDecodeError as e:
            err = ServerError(f"The server did not reply valid JSON. "
                              f"JSON exception: {str(e.args[0])}\n"
                              f"Full server response:\n\n"
                              f"{self._try_print_response_content(r)}", )
            raise err.with_traceback(e.__traceback__)

        except Exception as e:
            err = ServerError(f"Something went wrong downloading the new "+
                              f"configuration file from the server. " +
                              f"Full server response:\n\n"
                              f"{self._try_print_response_content(r)}")
            raise err.with_traceback(e.__traceback__)


    @retry(times=3, wait_for=10)
    def download_overlay_image(self, image_name: str) -> None:
        """ 
        Download an overlay image.
        """
        r = "[no response from server]"
        try:
            overlays_url = self.url + \
                            ("" if self.url.endswith("/") else "/") + \
                            REMOTE_IMAGES_PATH
            
            # Download from the server
            r = requests.get(f"{overlays_url}{image_name}",
                                stream=True,
                                auth=self.credentials,
                                timeout=REQUEST_TIMEOUT)

            # Report every error code as a failed download
            if r.status_code >= 400:
                raise ServerError(f"Failed to download overlay image '{image_name}'. "
                                  f"The server replied with status code "
                                  f"{r.status_code} ({r.reason}). "
                                  f"Check your server configuration for errors. "
                                  f"Full server response:\n\n"
                                  f"{self._try_print_response_content(r)}")

            # Save image to file
            r.raw.decode_content = True

            with open(IMAGE_OVERLAYS_PATH / image_name ,'wb') as f:
                shutil.copyfileobj(r.raw, f)
            log(f"New overlay image downloaded: {image_name}")

        except Exception as e:
            err = ServerError(f"Something went wrong downloading the "
                              f"overlay image '{image_name}'. "
                              f"Full server response:\n\n"
                              f"{self._try_print_response_content(r)}")
            raise err.with_traceback(e.__traceback__)


    def send_logs(self, path: Path):
        """ 
        Send the logs to the server.
        """
        logs = ""
        # Load the logs from file
        try:
            if os.path.exists(path):
                with open(path, "r") as l:
                    logs = l.readlines()
                    logs = "".join(logs)
        except Exception as e:
            log_error("Something went wrong opening the logs file. Sending a mock logfile.", e)
            logs = f"Failed to read the log file. Exception:\n\n" \
                   f"{traceback.format_exc()}\n"
            
        # Prevent the server from returning 'No logs detected' when the file is empty
        if logs == "":
            logs = ' ==> No logs found!! <== '
        
        r = {}
        try:
            # Send the logs
            data = {'logs': logs}
            r = requests.post(self.url, 
                            data=data, 
                            auth=self.credentials, 
                            timeout=REQUEST_TIMEOUT)

            if r.status_code >= 400:
                raise ServerError(
                    f"The server replied with status code {r.status_code} ({r.reason}). "
                    f"Check your server configuration for errors. "
                    f"Full server response:\n\n"
                    f"{self._try_print_response_content(r)}")
            try:
                response = r.json()
            except json.decoder.JSONDecodeError as e:
                err = ServerError(f"The server did not reply valid JSON. "
                                  f"JSON exception: {str(e.args[0])}\n"
                                  f"Full server response:\n\n"
                                  f"{self._try_print_response_content(r)}")
                raise err.with_traceback(e.__traceback__)

            # Make sure the server did not return an error
            reply = response.get("logs", "[No field named 'logs' in the response]")

            if reply != "" and reply != "Logs not detected":
                raise ServerError(
                    f"The server reply was unexpected. "
                    f"The reply message is: {str(reply)}\n" 
                    f"Full server response:\n\n"
                    f"{self._try_print_response_content(r)}")

        except Exception as e:
            err = ServerError(f"Something went wrong uploading the logs. "
                              f"Full server response:\n\n"
                              f"{self._try_print_response_content(r)}")
            raise err.with_traceback(e.__traceback__)


    def upload_picture(self, image_path: Path, image_name: str, image_extension: str) -> None:
        """
        Uploads the new picture to the server.
        """
        if not os.path.isfile(image_path):
            raise ServerError(f"No picture to upload at {image_path}")

        # Deal only with the date-time if max_photos = 0, otherwise rename and send.
        # The server will take care of numbering them if needed
        r = {}
        try:
            date_time = ""
            if not self.max_photos:
                date_time = datetime.datetime.now().strftime("_%Y-%m-%d_%H:%M:%S")
            final_image_name = f"{image_name}{date_time}.{image_extension}"
            final_image_path = Path(image_path).parent / final_image_name
            os.rename(image_path, final_image_path)

        except Exception as e:
            log_error("Something went wrong renaming the image. "\
                      f"It's going to be sent under its temporary name: {image_path}", e)
            final_image_path = image_path

        # Upload the picture
        try:
            files = {'photo': open(final_image_path, 'rb')}
            r = requests.post(self.url, 
                            files=files, 
                            auth=self.credentials,
                            timeout=REQUEST_TIMEOUT)

            if r.status_code >= 400:
                raise ServerError(
                    f"The server replied with status code {r.status_code} ({r.reason}). "
                    f"Check your server configuration for errors. "
                    f"Full server response:\n\n"
                    f"{self._try_print_response_content(r)}")
            try:
                response = r.json()
            except json.decoder.JSONDecodeError as e:
                err = ServerError(f"The server did not reply valid JSON. "
                                f"JSON exception: {str(e.args[0])}\n"
                                f"Full server response:\n\n"
                                f"{self._try_print_response_content(r)}", )
                raise err.with_traceback(e.__traceback__)
                        
            # Make sure the server did not return an error
            reply = response.get("photo", "[no field named 'photo' in the response]")
            if reply != "":
                raise ServerError(
                    f"The server reply was unexpected: the image probably didn't arrive. "
                    f"The reply is: {str(reply)}\n" 
                    f"Full server response:\n\n" 
                    f"{self._try_print_response_content(r)}")

            return final_image_path
        
        except Exception as e:
            err = ServerError(f"Something went wrong uploading the picture. "
                              f"Full server response:\n\n"
                              f"{self._try_print_response_content(r)}")
            raise err.with_traceback(e.__traceback__)
