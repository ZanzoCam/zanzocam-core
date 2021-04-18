from typing import Dict, List, Optional

import os
import sys
import math
import shutil
import requests
import datetime
import subprocess
from pathlib import Path
from textwrap import dedent

from constants import *
from webcam.utils import log, log_error, log_row
from webcam.configuration import Configuration


class System:
    """
    Monitor and manages the operating system.
    """
    
    def __init__(self):
        pass
    
    @staticmethod
    def report_general_status() -> Dict:
        """ 
        Collect general system data like version, uptime, internet connectivity. 
        In all cases, None means that the value could not be retrieved
        (i.e. an error occurred). Errors will be logged in the console with
        their stacktraces for further debug.
        """
        status = {}
        status["version"] = VERSION
        status["last reboot"] = System.get_last_reboot_time()
        status["uptime"] = System.get_uptime()
        status["hotspot"] = System.check_hotspot_allowed() or "FAILED (see stacktrace)"
        if status["hotspot"] != "OFF":
            status["autohotspot check"] = "OK" if System.run_autohotspot() else "FAILED (see stacktrace)"
        status['wifi ssid'] = System.get_wifi_ssid()
        status['internet access'] = System.check_internet_connectivity()
        status['disk size'] = System.get_filesystem_size()
        status['free disk space'] = System.get_free_space_on_disk()
        status['RAM status'] = System.get_ram_stats()
        return status


    @staticmethod
    def get_last_reboot_time() -> Optional[datetime.datetime]:
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
            log_error("Could not get last reboot datetime information", e)
        return None


    @staticmethod
    def get_uptime() -> Optional[datetime.timedelta]:
        """ 
        Read the uptime of ZANZOCAM as a timedelta object.
        Returns None if an error occurs.
        """
        try:
            last_reboot = System.get_last_reboot_time()
            return datetime.datetime.now() - last_reboot

        except Exception as e:
            log_error("Could not get uptime information", e)
        return None
        

    @staticmethod
    def check_hotspot_allowed() -> Optional[str]:
        """ 
        Checks whether ZANZOCAM can turn on its hotspot at need
        """
        if os.path.exists(HOTSPOT_FLAG):
            try:
                with open(HOTSPOT_FLAG, "r+") as h:
                    return h.read().strip()
            except Exception as e:
                log_error("Failed to check if the hotspot is allowed. "
                        "Assuming yes", e)
                return False
        else:
            log(f"Hotspot flag file not found. Creating it under {HOTSPOT_FLAG} with value ON")
            with open(HOTSPOT_FLAG, "w") as h:
                h.write("ON")
            return "No flag found, setting it to ON"


    @staticmethod
    def run_autohotspot() -> Optional[bool]:
        """
        Executes the autohotspot script to make sure to connect 
        to a new WiFi if so required.
        Returns True if connected to WiFi, False if on hotspot mode, 
        None if error.
        """
        try:
            hotspot_proc = subprocess.Popen(["/usr/bin/sudo", AUTOHOTSPOT_BINARY_PATH], 
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
            log_error("The hotspot script failed to run", e)
        return None


    @staticmethod
    def get_wifi_ssid() -> Optional[str]:
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
            log_error("Could not retrieve WiFi information", e)
        return None


    @staticmethod
    def check_internet_connectivity() -> Optional[bool]:
        """
        Verifies that there is Internet connection to the outside.
        Returns True if there is Internet connection, False if there isn't, 
        None if an error occurred during the test.
        """
        try:
            r = requests.head(CHECK_UPLINK_URL, timeout=REQUEST_TIMEOUT)
            return True
        except requests.ConnectionError as ex:
            return False
        except Exception as e:
            log_error("Could not check if there is Internet access", e)
        return None
        
        
    @staticmethod
    def get_filesystem_size() -> Optional[str]:
        """
        Returns a string with the size of the filesystem where the OS is running.
        Suffixes are KB, MB, GB, TB, Returns None if an error occurs.
        """
        try:
            fs_size, _, _ = shutil.disk_usage(__file__)
            return System.convert_bytes_into_string(fs_size)
        except Exception as e:
            log_error("Could not retrieve the size of the filesystem", e)
        return None
        
        
    @staticmethod
    def get_free_space_on_disk() -> Optional[str]:
        """
        Returns a string with the amount of free space left on the device.
        Suffixes are KB, MB, GB, TB, Returns None if an error occurs.
        """
        try:
            _, _, free_space = shutil.disk_usage(__file__)
            return System.convert_bytes_into_string(free_space)
        except Exception as e:
            log_error("Could not get the amount of free space on the filesystem", e)
        return None

        
    @staticmethod
    def get_ram_stats() -> Optional[str]:
        """
        Returns a string with some stats about the RAM and swap usage.
        Returns None if an error occurs.
        """
        try:
            mem_stats = ""
            with open("/proc/meminfo", 'r') as meminfo:
                for line in meminfo.readlines():
                    if line.startswith("MemTotal:"):
                        mem_stats += "total: " + line.replace("MemTotal:", "").strip() + " | "

                    elif line.startswith("MemFree:"):
                        mem_stats += "free: " + line.replace("MemFree:", "").strip() + " | "

                    elif line.startswith("MemAvailable:"):
                        mem_stats += "available: " + line.replace("MemAvailable:", "").strip() + " | "

                    elif line.startswith("SwapTotal:"):
                        mem_stats += "total swap: " + line.replace("SwapTotal:", "").strip() + " | "

                    elif line.startswith("SwapFree:"):
                        mem_stats += "free swap: " + line.replace("SwapFree:", "").strip() + " | "
            return mem_stats

        except Exception as e:
            log_error("Could not get the amount of free space on the filesystem", e)
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

    
    @staticmethod
    def copy_system_file(original_path: Path, backup_path: Path) -> bool:
        """
        Copies a file to a directory using sudo.
        Return True if the copy was successful, false otherwise
        """
        try:
            copy = subprocess.run([
                "/usr/bin/sudo", "cp", original_path, backup_path], 
                stdout=subprocess.PIPE)
            return True

            if not copy:
                raise ValueError("The cp process has failed. "
                                f"Execute 'sudo cp {original_path} {backup_path}' "
                                 "to replicate the issue")
        except Exception as e:
            log_error(f"Something went wrong creating copying {original_path} into {backup_path}. "
                        "The file hasn't been copied", e)
            return False 

    
    @staticmethod
    def give_ownership_to_root(file: Path):
        """
        Give ownership of the specified file to root.
        Return True if the chown process worked, False otherwise.
        """
        try:
            chown = subprocess.run([
                "/usr/bin/sudo", "chown", "root:root", file], 
                stdout=subprocess.PIPE)
            return True

            if not chown:
                raise ValueError("The chown process has failed. "
                                f"Execute 'sudo chown 'root:root' {file}' "
                                 "to replicate the issue")
        except Exception as e:
            log_error(f"Something went wrong assigning ownership of {file} to root. "
                       "The file ownership is probably unaffected", e)
            return False


    @staticmethod
    def apply_system_settings(configuration: Configuration) -> None:
        """
        Modifies the system according to the new configuration.
        """
        if 'time' in vars(configuration).keys():
            System.update_crontab(getattr(configuration, "time", {}))


    @staticmethod
    def prepare_crontab_string(time: Dict) -> List[str]:
        """
        Converts time directives from the configuration file into
        the content of the crontab itself.
        Return a list of strings, where each is a crontab line.
        """
        cron_strings = []

        # If a time in minutes is given, calculate the equivalent cron values
        frequency = time.get("frequency", "60")
        
        # Frequency might be zero, which means the crontab is set up manually
        if not frequency:
            cron_strings = [" ".join([
                time.get('minute', '*'),
                time.get('hour', '*'),
                time.get('day', '*'),
                time.get('month', '*'),
                time.get('weekday', '*')
            ])]
            return cron_strings

        # If the frequency is given, calculate all the cron strings
        start_time = time.get("start_activity", "00:00:00").split(":")[:2]
        stop_time = time.get("stop_activity", "23:59:00").split(":")[:2]

        # Converting each value into the total value in minutes
        try:
            frequency = int(frequency)
        except Exception as e:
            log_error("Could not convert the frequency value to minutes! Using fallback value of 10 minutes")
            frequency = 10
        
        try:
            start_total_minutes = int(start_time[0])*60 + int(start_time[1])
        except ValueError as e:
            log_error(f"Could not read start time ({start_time}) as a valid time! Setting it to midnight (00:00)")
            start_total_minutes = 0

        try:
            stop_total_minutes = int(stop_time[0])*60 + int(stop_time[1])
        except ValueError as e:
            log_error(f"Could not read stop time ({stop_time}) as a valid time! Setting it to midnight (23:59)")
            stop_total_minutes = 23*60 + 59

        # Compute every trigger time and save a cron string
        while(start_total_minutes < stop_total_minutes):
            hour = math.floor(start_total_minutes/60)
            minute = start_total_minutes - (hour*60)
            cron_strings.append(f"{minute} {hour} * * *")
            start_total_minutes += frequency

        return cron_strings

    
    @staticmethod
    def update_crontab(time: Dict) -> None:
        """ 
        Updates the crontab and tries to recover for potential issues.
        Might refuse to update it in case of misconfigurations, in which case it
        will restore the old one and log the exceptions.
        """
        # Get the crontab content
        cron_strings = System.prepare_crontab_string(time)   

        # Backup the old file
        backup_cron = System.copy_system_file(CRONJOB_FILE, BACKUP_CRONJOB)   
        
        # Creates a file with the right content
        with open(TEMP_CRONJOB, 'w') as d:
            d.writelines("# ZANZOCAM - shoot picture\n")
            for line in cron_strings:
                d.writelines(f"{line} {SYSTEM_USER} {sys.argv[0]}\n")

        # Move new cron file into cron folder
        System.copy_system_file(TEMP_CRONJOB, CRONJOB_FILE)

        # Assign the cron file to root:root
        chown_cron = System.give_ownership_to_root(CRONJOB_FILE)
        
        log("Crontab updated successfully")
            
        # if the ownership change failes, start recovery procedure:
        # Try to write back the old crontab
        if not chown_cron:
            log_error("Something went wrong changing the owner of the crontab!")
            log("Trying to restore the crontab using the backup.")
            
            log_row("+")
            if not backup_cron:
                log_error("The backup was not created!", 
                fatal="the crontab might not trigger anymore. "
                      "ZANZOCAM might need manual intervention.")
            else:
                restore_cron = System.copy_system_file(BACKUP_CRONJOB, CRONJOB_FILE)

                if not restore_cron:
                    log_error("Something went wrong restoring the cron file from its backup!",
                    fatal="the crontab might not trigger anymore. "
                          "ZANZOCAM might need manual intervention.")
                else:
                    log("cron file restored successfully. Please investigate the cause of the issue!")
            log_row("+")


    @staticmethod
    def generate_diagnostics(path = DIAGNOSTICS_LOG):
        """
        Generate a report with loads of system information, 
        to be sent to the server as a diagnostic tool.
        """
        report = dedent(f"""\
            ##############################
            #                            #
            #   ZANZOCAM - DIAGNOSTICS   #
            #                            #
            ##############################

            Date: {datetime.datetime.now()}

        """)
        report += "# ACTIVE PROCESSES\n"
        report += "###################\n\n"
        try:
            processes = subprocess.check_output(["/usr/bin/ps", "auxf"])
            report += processes.decode('utf-8')
        except Exception as e:
            report += "Nothing to show, exception occurred: {e}"

        report += "\n\n"
        report += "# RAM & MEMORY STATS\n\n"
        report += "#####################\n"
        try:
            with open("/proc/meminfo", 'r') as meminfo:
                for line in meminfo.readlines():
                    report += line
        except Exception as e:
            report += "Nothing to show, exception occurred: {e}"

        report += "\n\n"
        report += "# PORTS\n"
        report += "########\n\n"
        try:
            ports = subprocess.check_output(["/usr/bin/netstat", "patun"])
            report += ports.decode('utf-8')
        except Exception as e:
            report += "Nothing to show, exception occurred: {e}"

        report += "\n\n"
        report += "# CRONTABS\n"
        report += "############\n\n"
        #report += "User's crontabs\n\n"
        #crontabs = subprocess.check_output(["/usr/bin/crontab", "-l"])
        #report += crontabs.decode('utf-8')
        #report += "\n\n"

        report += "System crontabs:\n\n"
        #crontabs = subprocess.check_output(["/usr/bin/grep", "-vI", "/etc/cron.d/*"])
        #report += crontabs.decode('utf-8')
        try:
            _, _, crontabs = next(os.walk("/etc/cron.d/"))
            for crontab in crontabs:
                with open("/etc/cron.d/"+crontab, 'r') as c:
                    for line in c.readlines():
                        report += line
        except Exception as e:
            report += "Nothing to show, exception occurred: {e}"

        #report += "\n\n"
        #crontabs = subprocess.check_output(["/usr/bin/grep", "-vI", "/etc/cron.d/.*"])
        #report += crontabs.decode('utf-8')

        report += "\n\n"
        report += "# SYSTEMD UNITS\n\n"
        report += "################\n"
        try:
            systemd = subprocess.check_output(["/usr/bin/systemctl"])
            report += systemd.decode('utf-8')
        except Exception as e:
            report += "Nothing to show, exception occurred: {e}"

        report += "\n\n"
        report += "# INSTALLED PACKAGES\n"
        report += "#####################\n\n"
        try:
            packages = subprocess.check_output(["/usr/bin/apt", "list"])
            report += packages.decode('utf-8')
        except Exception as e:
            report += "Nothing to show, exception occurred: {e}"

        report += "\n\n"
        with open(path, 'w') as report_file:
            report_file.writelines(report)
