from typing import Any, List, Dict

import os
import random
from time import sleep
from pathlib import Path

from zanzocam.constants import (
    CONFIGURATION_FILE,
    CAMERA_LOG,
    IMAGE_OVERLAYS_PATH,
    RANDOM_UPLOAD_INTERVAL
)
from zanzocam.webcam.utils import log, log_error, retry
from zanzocam.webcam.configuration import Configuration
from zanzocam.webcam.server.http_server import HttpServer
from zanzocam.webcam.server.ftp_server import FtpServer
from zanzocam.webcam.errors import ServerError



class Server:
    """
    Handles all communications with the server.
    """
    def __init__(self, server_settings: Dict):

        if not server_settings:
            raise ServerError("No server information found in the "
                              "configuration file.")

        try:
            self.protocol = server_settings.get("protocol", None)
        # Occurs if 'parameters' is not a dict, like {'server': 'not a dict'}
        except AttributeError:
            self.protocol = None

        # Protect against protocol not being a string, where upper() would fail
        self.protocol = str(self.protocol).upper()

        if self.protocol.upper() == "HTTP":
            self._server = HttpServer(server_settings)

        elif self.protocol.upper() == "FTP":
            self._server = FtpServer(server_settings)

        else:
            raise ServerError("The communication protocol with the server "
                              "(HTTP, FTP) is not specified or not supported. "
                              "No protocol is available to estabilish a "
                              "connection to the server.")

    def get_endpoint(self):
        """
        Return a 'server agnostic' endpoint for logging purposes.
        """
        if self.protocol == "FTP":
            return f"ftp://{self._server.username}@{self._server.hostname}"
        elif self.protocol == "HTTP":
            return f"{self._server.url}"
        else:
            raise ValueError("No protocol defined, cannot render endpoint.")


    @retry(times=3, wait_for=10)
    def update_configuration(
        self, 
        old_configuration: Configuration,
        new_conf_path: Path = CONFIGURATION_FILE
    ) -> Configuration:
        """
        Download the new configuration file from the server and updates it
        locally. Takes care of backups.

        Returns either the new configuration or None in case of errors.
        """
        endpoint = self.get_endpoint()

        try:
            log(f"Downloading the new configuration file from {endpoint}")

            # Get the new configuration from the server
            configuration_data = self._server.download_new_configuration()

            # If the old server replied something good, it's OK to backup its data.
            old_configuration.backup()

            # Create new configuration object (overwrites configuration.json)
            configuration = Configuration.create_from_dictionary(
                configuration_data, path=new_conf_path)

            log("Configuration updated successfully.")
            return configuration

        except Exception as e:
            log_error("Something went wrong fetching the new configuration "
                      "from the server. Keeping the old configuration.", e)
        
        return None


    def download_overlay_images(self, images_list: List[str]) -> bool:
        """
        Download all the overlay images that should be re-downloaded.
        If it fails, logs it.

        Returns True in case of errors.
        """
        log(f"Downloading overlay images from '{self.get_endpoint()}' "
            f"into '{IMAGE_OVERLAYS_PATH}'")        

        if not images_list:
            log("No image overlays found, nothing to download.")
            return False

        log(f"Overlays to download: {images_list}")

        no_errors = True
        for image_name in images_list:
            try:
                self._server.download_overlay_image(image_name)

            except Exception as e:
                no_errors = False
                log_error(f"New overlay image failed to download: "
                          f"'{image_name}'. Ignoring it. This overlay "
                          f"image will not appear on the final image.", e)

        return no_errors


    @retry(times=3, wait_for=10)
    def upload_logs(self, path: Path = CAMERA_LOG):
        """
        Send the logs to the server.
        """
        try:
            self._server.send_logs(path)
            log(f"Logs uploaded successfully to {self.get_endpoint()}")
        except Exception as e:
            log_error("Something happened while uploading the logs "
                      f"to {self.get_endpoint()}", e,
                      fatal="Logs won't be uploaded.")


    @retry(times=5, wait_for=15)
    def upload_picture(self, image_path: Path, image_name: str,
                       image_extension: str, cleanup: bool = True) -> None:
        """
        Uploads the new picture to the server.
        """
        # Wait a random time, if enabled
        if RANDOM_UPLOAD_INTERVAL > 0:
            interval = random.randrange(0, RANDOM_UPLOAD_INTERVAL*10) / 10
            log(f"Waiting a random interval of {interval} sec to avoid server congestions.")
            sleep(interval)

        log(f"Uploading picture to {self.get_endpoint()}")
        try:
            if not image_name or not image_path or not image_extension:
                raise ValueError("Cannot upload the picture: "
                                f"picture name ({image_name}) "
                                f"or location ({image_path}) "
                                f"or extension ({image_extension}) "
                                f"not given.")

            # Make sure the file in question exists
            if not os.path.exists(image_path):
                raise ValueError("No picture to upload: "
                                f"{image_path} does not exist")

            # Upload the picture
            self.final_image_path = Path(
                self._server.upload_picture(
                    image_path, image_name, image_extension))
            log(f"Picture '{self.final_image_path.name}' uploaded successfully.")

            if cleanup:
                if os.path.exists(image_path):
                    os.remove(image_path)
                if os.path.exists(self.final_image_path):
                    os.remove(self.final_image_path)
                log("Pictures deleted successfully.")

        except Exception as e:
            log_error("Something happened uploading the picture! "
                      "It was probably not sent.", e,
                      fatal="The error was unexpected, can't fix. "
                      "The picture won't be uploaded.")


