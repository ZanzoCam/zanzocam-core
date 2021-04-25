from typing import Dict, List, Tuple, Optional

import os
import json
import shutil
from datetime import datetime
from pathlib import Path

from constants import *
from webcam.utils import log, log_error


class Configuration:
    """
    Manages the configurations.
    """
    def __init__(self, path: Path = CONFIGURATION_FILE):
        """
        Loads the data stored in the configuration file as object attributes
        for this instance.
        """
        if not os.path.exists(path) or not os.path.isfile(path):
            raise ValueError(f"No configuration file found under {path}. "
                              "Please configure the server data from the web "
                              "interface and try again")

        # Populate the attributes with the data
        self.send_diagnostics = False  # Fallback value, this attribute has to exist
        
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


    @staticmethod
    def create_from_dictionary(data: Dict, path: Path = CONFIGURATION_FILE) -> 'Configuration':
        """
        Creates a Configuration object starting from a dictionary. Will
        save the configuration file at the specified path.
        """
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


    def within_active_hours(self):
        """
        Compares the current time with the start-stop times and 
        return True if inside the interval, False if outside.
        """
        time_data = getattr(self, "time", {})

        try:
            current_time = datetime.strptime(
                            datetime.now().strftime("%H:%M"), 
                            "%H:%M") # remove date info
            start_time = datetime.strptime(self.get_start_time(), "%H:%M")
            stop_time = datetime.strptime(self.get_stop_time(), "%H:%M")

            # Extremes are included: it's intended
            if current_time >= start_time and current_time <= stop_time:
                return True
            return False

        except ValueError as e:
            log_error(f"Could not read the start-stop time values "
                      f"(start: {self.get_start_time()}, "
                      f"stop: {self.get_stop_time()}) as valid hours. "
                      f"We now assume this is an active time")
        return True


    def backup(self):
        """
        Creates a backup copy of the configuration file.
        """
        try:
            shutil.copy2(self._path, str(self._path) + ".bak")
        except Exception as e:
            log_error("Cannot backup the configuration file! "
                      "The current situation is dangerous, "
                      "please fix this error before a failure occurs", e)


    def restore_backup(self):
        """
        Restores the configuration file from its backup copy.
        """
        try:
            shutil.copy2(str(self._path) + ".bak", self._path)
        except Exception as e:
            log_error("Cannot restore the configuration file from its backup! "
                      "The current situation is dangerous, "
                      "please fix this error before a failure occurs " 
                      "(if it haven't happened already)", e)


    def overlays_to_download(self) -> List[str]:
        """
        List all the overlay images that should be downloaded from the server
        """
        overlays_block = getattr(self, "overlays", {})
        try:
            items = overlays_block.items()
        except AttributeError as e:
            log_error("The 'overlays' entry in the configuration file "
                      "does not correspond to a dictionary! Ignoring it.", e)
            return []

        to_download = []
        for position, data in getattr(self, "overlays", {}).items():
            if "path" in data.keys():
                to_download.append(data["path"])
        return to_download


    @staticmethod
    def _decode_json_values(json: Dict) -> Dict:
        """
        Ensures the JSON is parser properly: converts string numbers and
        string booleans into the correct types, recursively.
        """
        for key, value in json.items():
            # Recusrion
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
            json[key] = value
        return json
