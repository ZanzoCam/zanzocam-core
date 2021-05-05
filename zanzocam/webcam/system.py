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

        hotspot_allowed = System.check_hotspot_allowed()
        if hotspot_allowed:
            status["hotspot allowed"] = "YES"
        else:        
            status["hotspot allowed"] = "NO"

        if status["hotspot allowed"] != "NO":
            autohotspot_status = System.run_autohotspot()
            if autohotspot_status is None:
                status["hotspot status"] = "FAILED (see stacktrace)"
            else:
                if autohotspot_status:
                    status["hotspot status"] = "OFF (connected to WiFi)"
                else: 
                    status["hotspot status"] = "ON (no known WiFi in range)"

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
            
            if uptime_proc.returncode > 0:
                raise Exception(f"Process failed with return code "
                                f"{uptime_proc.returncode}. "
                                f"Stdout: {stdout}"
                                f"Stderr: {stderr}")

            last_reboot_string = stdout.decode('utf-8').strip()
            return datetime.datetime.strptime(last_reboot_string, 
                                              "%Y-%m-%d %H:%M:%S")

        except Exception as e:
            log_error("Could not get last reboot time information", e)
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
        Checks whether ZANZOCAM can turn on its hotspot at need.
        True if it can, False otherwise. 
        If the file was not found, it creates it with a value YES.
        In case of exceptions, defaults to True.
        """
        if os.path.exists(HOTSPOT_FLAG):
            try:
                with open(HOTSPOT_FLAG, "r+") as h:
                    content = h.read().strip()
                    if content.upper() == "YES":
                        return True
                    elif content.upper() == "NO":
                        return False
                    else:
                        log("The hostpot flag contains neither YES nor NO "
                            f"(it contains '{content}'). Please fix. "
                            "Assuming YES.")
                        return True

            except Exception as e:
                log_error("Failed to check if the hotspot is allowed. "
                        "Assuming YES", e)
                return True
        
        log(f"Hotspot flag file not found. Creating it under {HOTSPOT_FLAG}"
            f" with value YES")
        with open(HOTSPOT_FLAG, "w") as h:
            h.write("YES")
        return True


    @staticmethod
    def run_autohotspot() -> Optional[bool]:
        """
        Executes the autohotspot script to make sure to connect 
        to a new WiFi if so required.
        Returns True if connected to WiFi, False if on hotspot mode, 
        None if error.
        """
        try:
            hotspot_proc = subprocess.Popen([
                "/usr/bin/sudo", AUTOHOTSPOT_BINARY_PATH], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT)
            stdout, stderr = hotspot_proc.communicate()
            stdout = stdout.decode("utf-8")
            
            if hotspot_proc.returncode != 0:
                raise RuntimeError("The hotspot script returned with "
                                  f"exit code {hotspot_proc.returncode}.")
               
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

            if wifi_proc.returncode > 0:
                raise RuntimeError("iwgetid failed with code "
                                   f"{wifi_proc.returncode}")
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
            log_error("Could not get RAM data", e)
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
    def copy_system_file(source: Path, dest: Path) -> bool:
        """
        Copies a file to a directory using sudo.
        Return True if the copy was successful, False otherwise
        """
        copy = subprocess.run(
            ["/usr/bin/sudo", "cp", str(source), str(dest)], 
            stdout=subprocess.PIPE)

        if not copy or copy.returncode > 0:
            raise RuntimeError(f"The copy has failed. "
                               f"Stdout: {copy.stdout if copy else ''} "
                               f"Stderr: {copy.stderr if copy else ''} "
                               f"Execute 'sudo cp {source} {dest}' "
                               f"to replicate the issue")
    

    @staticmethod
    def give_ownership_to_root(path: Path):
        """
        Give ownership of the specified file to root.
        Return True if the chown process worked, False otherwise.
        """
        chown = subprocess.run([
            "/usr/bin/sudo", "chown", "root:root", str(path)], 
            stdout=subprocess.PIPE)

        if not chown or chown.returncode > 0:
            raise RuntimeError("The chown process has failed. "
                              f"Stdout: {chown.stdout if chown else ''} "
                              f"Stderr: {chown.stderr if chown else ''} "
                              f"Execute 'sudo chown root:root {path}' "
                              f"to replicate the issue")

    @staticmethod
    def remove_root_owned_file(path: Path):
        """
        Executes 'sudo rm <path>'
        Return True if the chown process worked, False otherwise.
        """
        chown = subprocess.run([
            "/usr/bin/sudo", "rm", str(path)], 
            stdout=subprocess.PIPE)

        if not chown or chown.returncode > 0:
            raise RuntimeError("The chown process has failed. "
                f"Stdout: {chown.stdout if chown else ''} "
                f"Stderr: {chown.stderr if chown else ''} "
                f"Execute 'sudo rm {path}' to replicate the issue")


    @staticmethod
    def apply_system_settings(system_settings: Dict) -> None:
        """
        Modifies the system according to the new configuration.
        """
        if 'time' in system_settings.keys():
            System.update_crontab(system_settings.get("time", {}))


    @staticmethod
    def prepare_crontab_string(time: Dict) -> List[str]:
        """
        Converts time directives from the configuration file into
        the content of the crontab itself.
        Return a list of strings, where each is a crontab line.
        """
        cron_strings = []

        # If a time in minutes is given, calculate the equivalent cron values
        try:
            frequency = time.get("frequency", "60")
            frequency = int(frequency)
        except ValueError:
            # the given frequency is not a number, warn and default
            log_error(f"frequency cannot be converted into int: {frequency}. "
                      f"Defaulting to 10 (one picture every 10 minutes)")
            frequency = 10

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
        try:
            cron_strings = System.prepare_crontab_string(time)   
        except Exception as e:
            log_error("Something happened assembling the crontab. "
                      "Aborting crontab update.", e)
            return

        # Backup the old file
        try:
            System.copy_system_file(CRONJOB_FILE, BACKUP_CRONJOB)   
        except Exception as e:
            log_error("Failed to backup the previous crontab! "
                      "In case of further errors it will be impossible to "
                      "restore it.", e)
            # Do not add a return here, this issue is secondary

        # Creates a file with the right content
        try:
            if os.path.exists(TEMP_CRONJOB):
                System.remove_root_owned_file(TEMP_CRONJOB)

            with open(TEMP_CRONJOB, 'w') as d:
                d.writelines("# ZANZOCAM - shoot picture\n")
                for line in cron_strings:
                    d.writelines(f"{line} {SYSTEM_USER} {sys.argv[0]}\n")
        except Exception as e:
            log_error("Failed to generate the new crontab. "
                      "Aborting crontab update.", e)
            return

        # Assign the cron file to root:root
        try:
            System.give_ownership_to_root(TEMP_CRONJOB)
        except Exception as e:
            log_error("Failed to assign the correct rights to the "
                      "new crontab file. Aborting crontab update.", e)
            return

        # Move new cron file into cron folder
        try:
            System.copy_system_file(TEMP_CRONJOB, CRONJOB_FILE)
        except Exception as e:
            log_error("Failed to replace the old crontab with a new one. "
                      "Aborting crontab update.", e)
            return

        log("Crontab updated successfully")


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
