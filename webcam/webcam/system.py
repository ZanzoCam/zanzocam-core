from typing import Dict, Optional

import os
import math
import shutil
import requests
import datetime
import subprocess
try:
    from importlib_metadata import version, PackageNotFoundError
except ModuleNotFoundError as e:
    from importlib.metadata import version, PackageNotFoundError
    
from webcam.constants import *
from webcam.utils import log, log_error
from webcam.configuration import Configuration


class System:
    """
    Monitor and manages the operating system.
    """
    
    def __init__(self):
        pass
    
    
    def report_general_status(self) -> Dict:
        """ 
        Collect general system data like version, uptime, internet connectivity. 
        In all cases, None means that the value could not be retrieved
        (i.e. an error occurred). Errors will be logged in the console with
        their stacktraces for further debug.
        """
        self.status = {}
        self.status["version"] = self.get_version()
        self.status["last reboot"] = self.get_last_reboot_time()
        self.status["uptime"] = self.get_uptime()
        self.status["hotspot"] = self.check_hotspot_allowed()
        if self.status["hotspot"] != "OFF":
            self.status["autohotspot check"] = self.run_autohotspot()
        self.status['wifi ssid'] = self.get_wifi_ssid()
        self.status['internet access'] = self.check_internet_connectivity()
        self.status['disk size'] = self.get_filesystem_size()
        self.status['free disk space'] = self.get_free_space_on_disk()
        return self.status

    def get_version(self) -> Optional[str]:
        """ 
        Read the ZANZOCAM version file 
        Returns None if an error occurs.
        """
        try:
            return version("zanzocam-webcam")
        except PackageNotFoundError as e:
            log("Could not get version information.", e)
        return None

    def get_last_reboot_time(self) -> Optional[datetime.datetime]:
        """ 
        Read the last reboot time of ZANZOCAM as a datetime object.
        Returns None if an error occurs.
        """
        try:
            uptime_proc = subprocess.Popen(['/usr/bin/uptime', '-s'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
            stdout, stderr = uptime_proc.communicate()
            
            last_reboot_string = stdout.decode('utf-8').strip()
            return datetime.datetime.strptime(last_reboot_string, "%Y-%m-%d %H:%M:%S")
            
        except Exception as e:
            log_error("Could not get last reboot datetime information.", e)
        return None
        
        
    def get_uptime(self) -> Optional[datetime.timedelta]:
        """ 
        Read the uptime of ZANZOCAM as a timedelta object.
        Returns None if an error occurs.
        """
        try:
            last_reboot = self.get_last_reboot_time()
            return datetime.datetime.now() - last_reboot

        except Exception as e:
            log_error("Could not get uptime information.", e)
        return None
        
        
    def check_hotspot_allowed(self) -> Optional[str]:
        """ 
        Checks whether ZANZOCAM can turn on its hotspot at need
        """
        try:
            with open("/home/zanzocam-bot/webcam/HOTSPOT_ALLOWED", "r+") as h:
                return h.read().strip()

        except Exception as e:
            log_error("Failed to check if the hotspot is allowed. "
                      "Assuming yes.", e)
            return False

    def run_autohotspot(self) -> Optional[bool]:
        """
        Executes the autohotspot script to make sure to connect 
        to a new WiFi if so required.
        Returns True if connected to WiFi, False if on hotspot mode, 
        None if error.
        """
        try:
            hotspot_proc = subprocess.Popen(["/usr/bin/sudo", "/usr/bin/autohotspot"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT)
            stdout, stderr = hotspot_proc.communicate()
            stdout = stdout.decode("utf-8")
            
            if hotspot_proc.returncode != 0:
                log_error("The hotspot script returned with exit code "
                          f"{hotspot_proc.returncode}.")
                return None
               
            wifi_is_active = [
                "Wifi already connected to a network",
                "Hotspot Deactivated, Bringing Wifi Up",
                "Connecting to the WiFi Network"
            ]
            if any(msg in stdout for msg in wifi_is_active):
                return True
                
            hotspot_is_active = [
                "No SSID, activating Hotspot",
                "Cleaning wifi files and Activating Hotspot",
                "Hostspot already active"
            ]
            if any(msg in stdout for msg in hotspot_is_active):
                return False
                
        except Exception as e:
            log_error("The hotspot script failed to run.", e)
        return None


    def get_wifi_ssid(self) -> Optional[str]:
        """
        Get the SSID of the WiFi it is connected to.
        Returns None if an error occurs and "" if the device is not connected
        to any WiFi network.
        """
        try:
            wifi_proc = subprocess.Popen(['/usr/sbin/iwgetid', '-r'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
            stdout, stderr = wifi_proc.communicate()

            # If the device is offline, iwgetid will return nothing.
            if not stdout:
                return ""
                            
            return stdout.decode('utf-8').strip()

        except Exception as e:
            log_error("Could not retrieve WiFi information.", e)
        return None


    def check_internet_connectivity(self) -> Optional[bool]:
        """
        Verifies that there is Internet connection to the outside.
        Returns True if there is Internet connection, False if there isn't, 
        None if an error occurred during the test.
        """
        try:
            r = requests.head("http://www.google.com", timeout=REQUEST_TIMEOUT)
            return True
        except requests.ConnectionError as ex:
            return False
        except Exception as e:
            log_error("Could not check if there is Internet access", e)
        return None
        
        
    def get_filesystem_size(self) -> Optional[str]:
        """
        Returns a string with the size of the filesystem where the OS is running.
        Suffixes are KB, MB, GB, TB, Returns None if an error occurs,
        """
        try:
            fs_size, _, _ = shutil.disk_usage(__file__)
            return self.convert_bytes_into_string(fs_size)
        except Exception as e:
            log_error("Could not retrieve the size of the filesystem.", e)
        return None
        
        
    def get_free_space_on_disk(self) -> Optional[str]:
        """
        Returns a string with the amount of free space left on the device.
        Suffixes are KB, MB, GB, TB, Returns None if an error occurs,
        """
        try:
            _, _, free_space = shutil.disk_usage(__file__)
            return self.convert_bytes_into_string(free_space)
        except Exception as e:
            log_error("Could not get the amount of free space on the filesystem.", e)
        return None


    @staticmethod
    def convert_bytes_into_string(bytes: int) -> str:
        """
        Convert an integer of bytes into a human readable string.
        """
        if bytes > 1024**4:
            return f"{bytes/(1024**4):.2f} TB"
        elif bytes > 1024**3:
            return f"{bytes/(1024**3):.2f} GB"
        elif bytes > 1024**2:
            return f"{bytes/(1024**2):.2f} MB"
        elif bytes > 1024:
            return f"{bytes/1024:.2f} KB"
        else:
            return f"{bytes} bytes"


    def apply_system_settings(self, configuration: Configuration) -> None:
        """
        Modifies the system according to the new configuration.
        """
        if 'crontab' in vars(configuration).keys() or 'time' in vars(configuration).keys():
            self.update_crontab(getattr(configuration, "time", {}), getattr(configuration, "crontab", {}))


    def update_crontab(self, time: Dict, cron: Dict) -> None:
        """ 
        Updates the crontab and tries to recover for potential issues.
        Might refuse to update it in case of misconfigurations, in which case it
        will restore the old one and log the exceptions.
        """
        cron_strings = []

        # If a time in minutes is given, calculate the equivalent cron values
        if time:
            frequency = time.get("frequency", "60")
            start_time = time.get("start_activity", "00:00:00").split(":")[:2]
            stop_time = time.get("stop_activity", "23:59:00").split(":")[:2]

            try:
                frequency = int(frequency)
            except Exception as e:
                log_error("Could not convert the frequency value to minutes! Using fallback value of 10 minutes")
                frequency = 10
            
            # Compute every trigger time and save a cron string
            start_total_minutes = int(start_time[0])*60 + int(start_time[1])
            stop_total_minutes = int(stop_time[0])*60 + int(stop_time[1])

            while(start_total_minutes < stop_total_minutes):
                hour = math.floor(start_total_minutes/60)
                minute = start_total_minutes - (hour*60)
                cron_strings.append(f"{minute} {hour} * * *")
                start_total_minutes += frequency

        # If instead cron is given, only create one string with the given cron parameters
        if cron:
            cron_strings = [" ".join([
                cron.get('minute', '*'),
                cron.get('hour', '*'),
                cron.get('day', '*'),
                cron.get('month', '*'),
                cron.get('weekday', '*')
            ])]
        
        # Creates a file with the right content
        with open(".tmp-cronjob-file", 'w') as d:
            d.writelines("# ZANZOCAM - shoot picture\n")
            for line in cron_strings:
                d.writelines(
                    f"{line} zanzocam-bot "
                    " /home/zanzocam-bot/venv/bin/z-webcam "
                    " >> /home/zanzocam-bot/webcam/logs.txt 2>&1\n")
                
        # Backup the old crontab in the home
        backup_cron = subprocess.run([
            "/usr/bin/sudo", 
            "mv", "/etc/cron.d/zanzocam", "/home/zanzocam-bot/.crontab.bak"], 
            stdout=subprocess.PIPE)
        if not backup_cron:
            log_error("Something went wrong creating a backup for the cron file. "
                      "No backup is created.")
            
        # Move new cron file into cron folder
        create_cron = subprocess.run([
            "/usr/bin/sudo", 
            "mv", ".tmp-cronjob-file", "/etc/cron.d/zanzocam"], 
            stdout=subprocess.PIPE)
        if not create_cron:
            log_error("Something went wrong creating the new cron file. "
                      "The old cron file should be unaffected.")

        # Give ownership of the new crontab file to root
        chown_cron = subprocess.run([
            "/usr/bin/sudo", 
            "chown", "root:root", "/etc/cron.d/zanzocam"], 
            stdout=subprocess.PIPE)
            
        log("Crontab updated successfully.")
            
        # if the ownership change failes, start recovery procedure:
        # Try to write back the old crontab
        if not chown_cron:
            log_error("Something went wrong changing the owner of the crontab!")
            log("Trying to restore the crontab using the backup")
            
            log("+++++++++++++++++++++++++++++++++++++++++++")
            if not backup_cron:
                log_error("The backup was not created!", 
                fatal="the crontab might not trigger anymore. "
                      "ZANZOCAM might need manual intervention.")
            else:
                restore_cron = subprocess.run([
                    "/usr/bin/sudo", 
                    "mv", "/home/zanzocam-bot/.crontab.bak", "/etc/cron.d/zanzocam"], 
                    stdout=subprocess.PIPE)
                    
                if not restore_cron:
                    log_error("Something went wrong restoring the cron file from its backup!",
                    fatal="the crontab might not trigger anymore. "
                          "ZANZOCAM might need manual intervention.")
                else:
                    log("cron file restored successfully.")
                    log("Please investigate the cause of the issue!")
            log("+++++++++++++++++++++++++++++++++++++++++++")
