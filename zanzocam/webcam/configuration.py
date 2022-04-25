from typing import Dict, List, Tuple, Optional

import os
import re
import json
import shutil
from datetime import datetime
from pathlib import Path

from zanzocam.constants import CONFIGURATION_FILE
from zanzocam.webcam.utils import log, log_error, AllStringEncoder


def load_configuration_from_disk(
    path = str(CONFIGURATION_FILE),
    backup_path = str(CONFIGURATION_FILE) + ".bak",
    quiet: bool = False
) -> Optional["Configuration"]:
    """
    Load current configuration from disk, 
    or try with its backup if the file is not found.

    Returns None if some error occurred.
    """
    try:
        if not quiet: log(f"Loading configuration from {path}...")
        return Configuration(path=path)

    except Exception as e:
        if isinstance(e, FileNotFoundError):
            log_error(str(e))  # Avoid stacktrace
        else:
            log_error("Failed to load configuration from "
                        f"'{CONFIGURATION_FILE}'.", e)

    try:
        log("Trying to load backup configuration...")
        return Configuration(path=backup_path)

    except Exception as e:
        if isinstance(e, FileNotFoundError):
            log_error(f"No backup configuration found under "
                        f"'{backup_path}'.")
        else:
            log_error(f"Failed to load the backup configuration from "
                        f"'{backup_path}'.", e)
    return None



class Configuration:
    """
    Manages the configurations.
    """
    def __init__(self, path: Path = CONFIGURATION_FILE):
        """
        Loads the data stored in the configuration file as object attributes
        for this instance.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"No configuration file found under {path}. "
                "Please configure the server data from the web "
                "interface and try again.")
        
        if not os.path.isfile(path):
            raise FileNotFoundError(
                f"The path {path} does not point to a file "
                "(is it a folder?). "
                "Please configure the server data from the web "
                "interface and try again.")

        # Read the configuration file
        # NOTE: a failure here *should* escalate, don't catch or rethrow
        with open(path, 'r') as c:
            configuration = json.load(c)
            configuration = self._decode_json_values(configuration)

            for key, value in configuration.items():
                setattr(self, key, value)

        # Add info about the download time (last edit time)
        self._download_time = datetime.fromtimestamp(Path(path).stat().st_mtime)
        self._path = path
        self._backup_path = str(path) + ".bak"


    @staticmethod
    def create_from_dictionary(data: Dict, path: Path = None) -> 'Configuration':
        """
        Creates a Configuration object starting from a dictionary. Will
        save the configuration file at the specified path.
        """
        if not path:
            path = CONFIGURATION_FILE

        data = Configuration._decode_json_values(data)  # Transform strings into numbers
        with open(path, "w+") as d:
            json.dump(data, d, indent=4)

        return Configuration(path)

        
    def __str__(self):
        """
        Prints out as a JSON object
        """
        return json.dumps(vars(self), indent=4, default=lambda x: str(x))


    def get_start_time(self):
        """
        Return either the start time defined, or 00:00
        """
        time_data = getattr(self, "time", {})
        return time_data.get("start_activity", "00:00")


    def get_stop_time(self):
        """
        Return either the stop time defined, or 23:59
        """
        time_data = getattr(self, "time", {})
        return time_data.get("stop_activity", "23:59")


    def get_server_settings(self):
        """
        Return all the information relative to the settings 
        used to connect to the server.
        """
        server_data = getattr(self, "server", {})
        return server_data


    def get_camera_settings(self):
        """
        Return all the information relative to the settings 
        used to take and render the picture.
        """
        image_data = getattr(self, "image", {})
        overlays_data = getattr(self, "overlays", {})
        return {
            'image': image_data,
            'overlays': overlays_data
        }

    def get_system_settings(self):
        """
        Return all the information relative to the settings 
        that should be applied to the system.

        For now is just the time settings.
        """
        time_data = getattr(self, "time", {})
        return {
            'time': time_data
        }

    def within_active_hours(self) -> Optional[bool]:
        """
        Compares the current time with the start-stop times.

        Returns True if inside the interval, False if outside, 
        None if an error occured.
        """
        try:
            log(f"Checking if {datetime.now().strftime('%H:%M')} "
                f"is into active interval "
                f"({self.get_start_time()} to "
                f"{self.get_stop_time()}).")

            current_time = datetime.strptime(
                            datetime.now().strftime("%H:%M"), 
                            "%H:%M") # remove date info
            start_time = datetime.strptime(self.get_start_time(), "%H:%M")
            stop_time = datetime.strptime(self.get_stop_time(), "%H:%M")

            # Extremes are included: it's intended
            if current_time >= start_time and current_time <= stop_time:
                log("The current time is inside active hours.")
                return True

            log("The current time is outside active hours.")
            return False

        except ValueError as e:
            log_error(f"Could not read the start-stop time values "
                      f"(start: {self.get_start_time()}, "
                      f"stop: {self.get_stop_time()}) as valid hours.")
        except Exception as e:
            log_error(f"Something unexpected has occured trying to find out "
                       "if this is active time for the ZanzoCam. "
                       "Check the stacktrace!", e)
        return None



    def backup(self, path: str = None):
        """
        Creates a backup copy of the configuration file.

        NOTE: we backup from memory and not simply copy the file
        because the file might have been overwritten by a server
        (server.update_configuration()) in the meantime.
        """
        # If path is not given, use the default one defined at init
        if path:
            self._backup_path = path
        
        try:
            backup_vars = {
                k: v 
                    for k, v in vars(self).items() 
                    if not k.startswith("_")    
                }
            with open(self._backup_path, 'w') as backup:
                json.dump(backup_vars, backup, indent=4, cls=AllStringEncoder)

        except Exception as e:
            log_error("Cannot backup the configuration file! "
                      "The current situation is dangerous, "
                      "please fix this error before a failure occurs", e)


    def restore_backup(self) -> bool:
        """
        Restores the configuration file from its backup copy.
        Does not try to reload the old config.

        Returns True in case of no errors, False otherwise.
        """
        try:
            shutil.copy2(self._backup_path, self._path)
        except Exception as e:
            log_error("Cannot restore the configuration file from its backup! "
                      "The current situation is dangerous, "
                      "please fix this error before a failure occurs " 
                      "(if it haven't happened already)", e)
            return False
        return True


    def list_overlays(self) -> List[str]:
        """
        List all the overlay images that should be downloaded from the server
        """
        log("Scanning the configuration for overlays...")

        overlays_block = getattr(self, "overlays", {})
        if not isinstance(overlays_block, dict):
            log_error("The 'overlays' entry in the configuration "
                      "is not a dictionary! Ignoring it.")
            return []

        paths = []
        for position, data in getattr(self, "overlays", {}).items():
            if "path" in data.keys():
                
                path = str(data["path"]).strip()
                if not path or path == "":
                    log_error(f"Overlay image in position {position} has "
                              f"no path! Ignoring it.")
                    continue

                log(f"Found image overlay: {path}")
                paths.append(path)

        return paths


    @staticmethod
    def _decode_json_values(json: Dict) -> Dict:
        """
        Ensures the JSON is parser properly: converts string numbers and
        string booleans into the correct types, recursively.
        """
        decoded_json = {}
        for key, value in json.items():
            # Check keys: only alphanumeric and underscore allowed, 
            # the rest get converted into underscore
            key = re.sub('[^0-9a-zA-Z]+', '_', key)
            # Recursion
            if isinstance(value, dict):
                value = Configuration._decode_json_values(value)
            # Check if string boolean
            if isinstance(value, str):
                if value.lower() == "false":
                    value = False
                elif value.lower() == "true":
                    value = True
                else:
                    # Check if string number
                    try:
                        value = float(value)
                        value = int(value)
                    except ValueError:
                        pass
            decoded_json[key] = value
        return decoded_json
