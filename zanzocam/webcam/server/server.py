from typing import Any, List, Dict

import os
import json
from time import sleep
from pathlib import Path
from functools import wraps

from zanzocam.constants import (
    CONFIGURATION_FILE,
    FAILURE_REPORT_PATH,
    CAMERA_LOG
)
from zanzocam.webcam.utils import log, log_error
from zanzocam.webcam.configuration import Configuration
from zanzocam.webcam.server.http_server import HttpServer
from zanzocam.webcam.server.ftp_server import FtpServer
from zanzocam.webcam.errors import ServerError


def retry(times: int, wait_for: float):
    """
    Makes the decorated function try to run without
    exceptions 'times' times.
    If an exception occurs, logs it and tries again
    after `wait_for` seconds.
    Otherwise returns at the first successful attempt.
    """
    def retry_decorator(func):
        @wraps(func)
        def retry_wrapper(*args, **kwargs):

            exception = None
            for i in range(times):
                try:
                    return func(*args, **kwargs)

                except Exception as e:
                    exception = e
                    log_error("An exception occurred!", e)
                    log(f"Waiting for {wait_for} sec. "
                        "and retrying...")
                    sleep(wait_for)

            raise exception
        return retry_wrapper
    return retry_decorator


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
    def update_configuration(self, old_configuration: Configuration,
                             new_conf_path: Path = None) -> Configuration:
        """
        Download the new configuration file from the server and updates it
        locally.
        """
        if not new_conf_path:
            new_conf_path = CONFIGURATION_FILE

        # Get the new configuration from the server
        configuration_data = self._server.download_new_configuration()

        # If the old server replied something good, it's OK to backup its data.
        old_configuration.backup()

        # Create new configuration object (overwrites configuration.json)
        configuration = Configuration.create_from_dictionary(
            configuration_data, path=new_conf_path)

        return configuration

    @retry(times=3, wait_for=10)
    def download_overlay_images(self, images_list: List[str]) -> None:
        """
        Download all the overlay images that should be re-downloaded.
        If it fails, logs it.
        """
        for image_name in images_list:
            try:
                self._server.download_overlay_image(image_name)

            except Exception as e:
                log_error(f"New overlay image failed to download: "
                          f"'{image_name}'. Ignoring it. This overlay "
                          f"image will not appear on the final image.", e)

    @retry(times=3, wait_for=10)
    def upload_logs(self, path: Path = None):
        """
        Send the logs to the server.
        """
        if not path:
            path = CAMERA_LOG

        self._server.send_logs(path)

        # Clear the logs once they have been uploaded
        with open(path, "w") as _:
            pass

    @retry(times=3, wait_for=10)
    def upload_failure_report(self,
                              wrong_conf: Dict[str, Any],
                              right_conf: Dict[str, Any],
                              logs_path: Path = None) -> None:
        """
        Send a report of the failure to the old server.
        """
        if not logs_path:
            logs_path = CAMERA_LOG

        logs = ""
        try:
            if os.path.exists(logs_path):
                with open(logs_path, "r") as logs_file:
                    logs = logs_file.read()
        except Exception as e:
            log_error("Something went wrong opening the logs file."
                      "The report will contain no logs.", e)
            logs = "An error occurred opening the logs file and the logs " \
                   "could not be read."

        if not logs or logs == "":
            logs = " ==> No logs found <== "

        with open(FAILURE_REPORT_PATH, "w") as report:
            report.write(
                "**********************\n"
                "*   FAILURE REPORT   *\n"
                "**********************\n"
                "Failed to use the server information contained in the new "
                "configuration file.\n"
                "New, NOT working server information is the following:\n" +
                json.dumps(wrong_conf, indent=4) +
                "\nPlease fix the above information in the configuration "
                "file or fix the affected server.\n"
                "ZANZOCAM will keep trying to download a new config with "
                "this parameters instead:\n" +
                json.dumps(right_conf, indent=4) +
                "\nHere below is the log of the last run before the crash.\n\n"
                "**********************\n\n" +
                logs +
                "\n\n**********************\n"
            )

        # Send the logs
        self._server.send_logs(FAILURE_REPORT_PATH)
        # Clear the report once it has been uploaded
        with open(FAILURE_REPORT_PATH, "w") as logs:
            pass

    @retry(times=5, wait_for=15)
    def upload_picture(self, image_path: Path, image_name: str,
                       image_extension: str, cleanup: bool = True) -> None:
        """
        Uploads the new picture to the server.
        """
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
