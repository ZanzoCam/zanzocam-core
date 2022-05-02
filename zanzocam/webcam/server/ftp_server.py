from typing import Any, List, Dict, Optional

import os
import json
import shutil
import datetime
import requests
from ftplib import FTP, FTP_TLS, error_perm
from json import JSONDecodeError

from zanzocam.constants import *
from zanzocam.webcam.utils import log, log_error, retry
from zanzocam.webcam.configuration import Configuration
from zanzocam.webcam.errors import ServerError



class FtpServer:
    """
    Handles all communication with the server over an FTP connection.
    """
    def __init__(self, parameters: Dict[str, str]):
        if not isinstance(parameters, dict):
            raise ValueError("FtpServer can only be instantiated with a dictionary.")

        # host is necessary
        self.hostname = parameters.get("hostname")
        if not self.hostname:
            raise ServerError("Cannot contact the server: "
                              "no hostname found in the configuration")

        # username is necessary
        self.username = parameters.get("username")
        if not self.username:
            raise ServerError("Cannot contact the server: "
                              "no username found in the configuration.")

        # password can be blank  (TODO really it can? Check)
        self.password = parameters.get("password", "")
        self.tls = parameters.get("tls", True)
        self.subfolder = parameters.get("subfolder")
        self.max_photos = parameters.get("max_photos", 0)

        # Estabilish the FTP connection
        try:
            if self.tls:
                self._ftp_client = _Patched_FTP_TLS(host=self.hostname, 
                                                    user=self.username, 
                                                    passwd=self.password, 
                                                    timeout=REQUEST_TIMEOUT*2)
                self._ftp_client.prot_p()  # Set up secure data connection.
            else:
                self._ftp_client = FTP(host=self.hostname, 
                                        user=self.username, 
                                        passwd=self.password, 
                                        timeout=REQUEST_TIMEOUT*2)
            if self.subfolder:
                self._ftp_client.cwd(self.subfolder)
                
        except Exception as e:
            raise ServerError("Failed to estabilish a connection "
                              "with the FTP server") from e
        

    def download_new_configuration(self) -> Dict[str, Any]:
        """
        Download the new configuration file from the server.
        """
        self.configuration_string = ""

        # Callback for the incoming data
        def store_line(line):
            self.configuration_string += line.decode(FTP_CONFIG_FILE_ENCODING)

        # Fetch the new config
        response = self._ftp_client.retrbinary("RETR configuration/configuration.json", store_line)

        # Make sure the server did not reply with an error
        if "226" in response:
            configuration_data = json.loads(self.configuration_string)
            self.configuration_string = ""
            return configuration_data
            
        raise ServerError("The server replied with an error code: " + response)
            
    @retry(times=3, wait_for=10)
    def download_overlay_image(self, image_name: str) -> None:
        """ 
        Download an overlay image.
        """
        with open(IMAGE_OVERLAYS_PATH / image_name ,'wb') as overlay:
            response = self._ftp_client.retrbinary(
                            f"RETR {REMOTE_IMAGES_PATH}{image_name}", overlay.write)
        if not "226" in response:
            raise ServerError(f"The server replied with an error code for '{image_name}': " + response)
        log(f"New overlay image downloaded: {image_name}")
        

    def send_logs(self, path: Path):
        """ 
        Send the logs to the server.
        """
        # Make sure the file in question exists and has some content
        try:
            if not os.path.exists(path) or open(path, "r").read().strip() == "":
                with open(path, "w") as l:
                    l.writelines(" ==> No logs found!! <==")
        except Exception as e:
            log_error("No logs were found and no mock log file can be written."
                      "Logs won't be uploaded.", e)
            return
        
        # Fetch the new overlay
        with open(path ,'rb') as logs:
            response = self._ftp_client.storlines(
                f"STOR logs/logs_{datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%s')}.txt", logs)
                
        # Make sure the server did not reply with an error
        if not "226" in response:
            raise ServerError(f"The server replied with an error code while " +
                            "uploading the logs: " + response)


    def upload_picture(self, image_path: Path, image_name: str, image_extension: str) -> str:
        """
        Uploads the new picture to the server.
        Returns the final image path (for cleanup operations)
        """
        if not os.path.isfile(image_path):
            raise ServerError(f"No picture to upload at {image_path}")
        
        # Rename the picture according to max_photos
        modifier = ""
        if self.max_photos == 0:
            modifier = datetime.datetime.now().strftime("_%Y-%m-%d_%H:%M:%S")
        elif self.max_photos > 1:
            modifier = "__0"
        final_image_name = image_name + modifier + "." + image_extension
        final_image_path = Path(image_path).parent / final_image_name
        os.rename(image_path, final_image_path)

        # If the server is supposed to contain only a fixed amount of pictures,
        # apply the prefix to this one and scale the other pictures' prefixes.
        # NOTE that in the HTTP version this is done by the PHP script
        if self.max_photos > 1:

            # Renaming images in reverse order, not to overwreite each other.
            # The first -1 is because extremes are excluded
            # The second -1 is the step
            # This procedure will also overwrite the oldest picture
            log("Renaming pictures of the server...")
            for position in range(self.max_photos-1, -1, -1):
                
                old_name = f"{image_name}__{position}.{image_extension}"
                new_name = f"{image_name}__{position+1}.{image_extension}"
                
                try:
                    self._ftp_client.rename(f"pictures/{old_name}", f"pictures/{new_name}")
                except Exception as e:
                    if '550' in str(e):
                        log(f"Error: {str(e)}. Probably the image didn't exist. Ignoring.")
                        
        # Upload the picture
        response = self._ftp_client.storbinary(
            f"STOR pictures/{final_image_name}", open(final_image_path ,"rb"))
                
        # Make sure the server did not reply with an error
        if not "226" in response:
            raise ServerError("The server replied with an error code while " +
                            "uploading the picture. The image was probably not sent! " +
                            "FTP Error: " + response)
            
        return final_image_path



class _Patched_FTP_TLS(FTP_TLS):
    """
    Explicit FTP_TLS version with shared TLS session. 
    Used to counteract "buggy" (or at least unusual) configuration on PureFTPd servers.
    For reference: https://bugs.python.org/issue19500
                   https://stackoverflow.com/questions/12164470/python-ftp-implicit-tls-connection-issue
                   https://stackoverflow.com/questions/14659154/ftpes-session-reuse-required  --> fix comes from here
    """
    def ntransfercmd(self, cmd, rest=None):
        conn, size = FTP.ntransfercmd(self, cmd, rest)
        if self._prot_p:
            conn = self.context.wrap_socket(conn,
                                            server_hostname=self.host,
                                            session=self.sock.session)  # this is the fix
        return conn, size
