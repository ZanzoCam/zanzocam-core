import os
import sys
import math
import pytest
import requests
import builtins
from unittest import mock
from freezegun import freeze_time
from datetime import datetime, timedelta

import zanzocam.webcam as webcam
import zanzocam.constants as constants
from zanzocam.webcam import system

from tests.conftest import in_logs


def test_get_last_reboot_time_success(fake_process, logs):
    """
        Get the last reboot time, test normal behavior
    """
    mock_time = b"2021-01-01 00:00:00"
    fake_process.register_subprocess(
        ['/usr/bin/uptime', '-s'], stdout=mock_time
    )
    last_reboot_time = system.get_last_reboot_time()
    date_format = "%Y-%m-%d %H:%M:%S"
    expected_time = datetime.strptime(mock_time.decode('utf-8'), date_format)
    assert last_reboot_time == expected_time
    assert len(logs) == 0


def test_get_last_reboot_time_exception(fake_process, logs):
    """
        Get the last reboot time, test exception management
    """
    mock_time = b"2021-01-01 00:00:00"    
    fake_process.register_subprocess(
        ['/usr/bin/uptime', '-s'], returncode=2
    )
    last_reboot_time = system.get_last_reboot_time()
    assert last_reboot_time == None
    assert len(logs) == 1
    assert in_logs(logs, "Could not get last reboot time information")


@freeze_time("2021-01-01 12:00:00")
def test_get_uptime_success(fake_process, logs):
    """
        Get the uptime, test normal behavior
    """
    mock_time = b"2021-01-01 00:00:00"
    fake_process.register_subprocess(
        ['/usr/bin/uptime', '-s'], stdout=mock_time
    )
    uptime = system.get_uptime()
    assert uptime == timedelta(hours=12)
    assert len(logs) == 0


def test_get_uptime_exception(fake_process, logs):
    """
        Get the uptime, test exception management
    """
    mock_time = b"2021-01-01 00:00:00"
    fake_process.register_subprocess(
        ['/usr/bin/uptime', '-s'], returncode=2
    )
    uptime = system.get_uptime()
    assert uptime == None
    assert len(logs) == 2
    assert in_logs(logs, "Could not get uptime information")
    assert in_logs(logs, "Could not get last reboot time information")


def test_check_hotspot_allowed_flag_set_to_yes(logs):
    """
        Check if the hotspot is allowed, test YES flag
    """
    with open(constants.HOTSPOT_FLAG, 'w') as f:
        f.write("yes")
    allowed = system.check_hotspot_allowed()
    assert allowed
    assert len(logs) == 0


def test_check_hotspot_allowed_flag_set_to_no(logs):
    """
        Check if the hotspot is allowed, test NO flag
    """
    with open(constants.HOTSPOT_FLAG, 'w') as f:
        f.write("no")
    allowed = system.check_hotspot_allowed()
    assert not allowed
    assert len(logs) == 0 


def test_check_hotspot_allowed_flag_set_to_other(logs):
    """
        Check if the hotspot is allowed, test unexpected flag
    """
    with open(constants.HOTSPOT_FLAG, 'w') as f:
        f.write("Other")
    allowed = system.check_hotspot_allowed()
    assert allowed
    assert len(logs) == 1
    assert in_logs(logs, "The hostpot flag contains neither YES nor NO")


def test_check_hotspot_allowed_permission_error(logs):
    """
        Check if the hotspot is allowed, test permission errors
    """
    with open(constants.HOTSPOT_FLAG, 'w') as f:
        f.write("no")
    os.chmod(constants.HOTSPOT_FLAG, 0o222)
    allowed = system.check_hotspot_allowed()
    assert allowed
    assert len(logs) == 1
    assert in_logs(logs, "Failed to check if the hotspot is allowed")


def test_check_hotspot_allowed_no_file(logs):
    """
        Check if the hotspot is allowed, no file
    """
    assert not os.path.exists(constants.HOTSPOT_FLAG)
    allowed = system.check_hotspot_allowed()
    assert allowed
    assert len(logs) == 1
    assert in_logs(logs, "Hotspot flag file not found")
    assert os.path.exists(constants.HOTSPOT_FLAG)
    assert open(constants.HOTSPOT_FLAG, 'r').read() == "YES"


def test_run_hotspot_on_wifi_1(fake_process, logs):
    """
        Check if the hotspot runs, normal behavior on wifi.
    """
    fake_process.register_subprocess(
        ["/usr/bin/sudo", constants.AUTOHOTSPOT_BINARY_PATH], 
        stdout="Wifi already connected to a network"
    )
    assert system.run_autohotspot()
    assert len(logs) == 0


def test_run_hotspot_on_wifi_2(fake_process, logs):
    """
        Check if the hotspot runs, turning off hotspot to go on wifi.
    """
    fake_process.register_subprocess(
        ["/usr/bin/sudo", constants.AUTOHOTSPOT_BINARY_PATH], 
        stdout="Hotspot Deactivated, Bringing Wifi Up"
    )
    assert system.run_autohotspot()
    assert len(logs) == 0


def test_run_hotspot_on_wifi_3(fake_process, logs):
    """
        Check if the hotspot runs, connecting to wifi for the first time.
    """
    fake_process.register_subprocess(
        ["/usr/bin/sudo", constants.AUTOHOTSPOT_BINARY_PATH], 
        stdout="Connecting to the WiFi Network"
    )
    assert system.run_autohotspot()
    assert len(logs) == 0


def test_run_hotspot_on_hotspot_1(fake_process, logs):
    """
        Check if the hotspot runs, normal behavior on hotspot
    """
    fake_process.register_subprocess(
        ["/usr/bin/sudo", constants.AUTOHOTSPOT_BINARY_PATH], 
        stdout="Hostspot already active"
    )
    result = system.run_autohotspot()
    assert result is not None
    assert not result
    assert len(logs) == 0


def test_run_hotspot_on_hotspot_2(fake_process, logs):
    """
        Check if the hotspot runs, turning off wifi to go on hotspot.
    """
    fake_process.register_subprocess(
        ["/usr/bin/sudo", constants.AUTOHOTSPOT_BINARY_PATH], 
        stdout="Cleaning wifi files and Activating Hotspot"
    )
    result = system.run_autohotspot()
    assert result is not None
    assert not result
    assert len(logs) == 0


def test_run_hotspot_on_hotspot_3(fake_process, logs):
    """
        Check if the hotspot runs, turning on hotspot.
    """
    fake_process.register_subprocess(
        ["/usr/bin/sudo", constants.AUTOHOTSPOT_BINARY_PATH], 
        stdout="No SSID, activating Hotspot"
    )
    result = system.run_autohotspot()
    assert result is not None
    assert not result
    assert len(logs) == 0


def test_run_hotspot_script_failure(fake_process, logs):
    """
        Check if the hotspot runs, turning on hotspot.
    """
    fake_process.register_subprocess(
        ["/usr/bin/sudo", constants.AUTOHOTSPOT_BINARY_PATH], 
        returncode=2
    )
    assert system.run_autohotspot() is None
    assert len(logs) == 1
    assert in_logs(logs, "The hotspot script failed to run")


def test_get_wifi_data_success(fake_process, logs):
    """
        Check if we can get wifi information under normal conditions
    """
    ssid = """
    wlan0       IEEE 802.11  ESSID:"TestWifi"  
                Mode:Managed  Frequency:2.472 GHz  Access Point: 80:16:05:06:8D:61   
                Bit Rate=28.8 Mb/s   Tx-Power=31 dBm   
                Retry short limit:7   RTS thr:off   Fragment thr:off
                Power Management:on
                Link Quality=48/70  Signal level=-62 dBm  
                Rx invalid nwid:0  Rx invalid crypt:0  Rx invalid frag:0
                Tx excessive retries:1015  Invalid misc:0   Missed beacon:0
    """
    fake_process.register_subprocess(
        ['/usr/sbin/iwconfig', 'wlan0'], stdout=ssid
    )
    assert system.get_wifi_data() == {
        "ssid": "TestWifi",
        "frequency": "2.472 GHz",
        "access point": "80:16:05:06:8D:61",
        "bit rate": "28.8 Mb/s",
        "tx power": "31 dBm",
        "link quality": "48/70",
        "signal level": "-62 dBm"
    }
    assert len(logs) == 0


def test_get_wifi_data_no_wifi(fake_process, logs):
    """
        Check if we can get wifi information when the device
        is not connected to any wifi (iwgetid returns nothing)
    """
    fake_process.register_subprocess(
        ['/usr/sbin/iwconfig', 'wlan0'],
    )
    assert system.get_wifi_data() == {
        "ssid": "n/a",
        "frequency": "n/a",
        "access point": "n/a",
        "bit rate": "n/a",
        "tx power": "n/a",
        "link quality": "n/a",
        "signal level": "n/a"
    }
    assert len(logs) == 0


def test_get_wifi_data_exception(fake_process, logs):
    """
        Check if we can get wifi information, behavior on exception.
    """
    fake_process.register_subprocess(
        ['/usr/sbin/iwgetid', '-r'], returncode=2
    )
    assert system.get_wifi_data() is None
    assert len(logs) == 1
    assert in_logs(logs, "Could not retrieve WiFi information")


def test_check_internet_connectivity_success(monkeypatch, logs):
    """
        Check uplink, normal conditions.
    """
    def alright(url, timeout):
        pass

    monkeypatch.setattr(webcam.system.requests, "head", alright)
    assert system.check_internet_connectivity()
    assert len(logs) == 0


def test_check_internet_connectivity_timeout(monkeypatch, logs):
    """
        Check uplink, request times out.
    """
    def timeout(url, timeout):
        raise requests.ConnectionError()

    monkeypatch.setattr(webcam.system.requests, "head", timeout)
    assert not system.check_internet_connectivity()
    assert len(logs) == 0


def test_check_internet_connectivity_exception(monkeypatch, logs):
    """
        Check uplink, other exception.
    """
    def generic_error(url, timeout):
        raise ValueError()

    monkeypatch.setattr(webcam.system.requests, "head", generic_error)
    assert not system.check_internet_connectivity()
    assert len(logs) == 1
    assert in_logs(logs, "Could not check if there is Internet access")


def test_get_filesystem_size_success(monkeypatch, logs):
    """
        Get the filesystem size, normal conditions
    """
    def alright(path):
        return 5*(1024**3), 0, 0

    monkeypatch.setattr(webcam.system.shutil, "disk_usage", alright)
    assert system.get_filesystem_size() == "5.00 GB"
    assert len(logs) == 0


def test_get_filesystem_size_exception(monkeypatch, logs):
    """
        Get the filesystem size, behavior on exception
    """
    def generic_exception(path):
        raise PermissionError()

    monkeypatch.setattr(webcam.system.shutil, "disk_usage", generic_exception)
    assert system.get_filesystem_size() is None
    assert len(logs) == 1
    assert in_logs(logs, "Could not retrieve the size of the filesystem")


def test_get_free_space_on_disk_success(monkeypatch, logs):
    """
        Get the amount of free space left, normal conditions
    """
    def alright(path):
        return 0, 0, 900*(1024**2)

    monkeypatch.setattr(webcam.system.shutil, "disk_usage", alright)
    assert system.get_free_space_on_disk() == "900.00 MB"
    assert len(logs) == 0


def test_get_free_space_on_disk_exception(monkeypatch, logs):
    """
        Get the amount of free space left, behavior on exception
    """
    def generic_exception(path):
        raise PermissionError()

    monkeypatch.setattr(webcam.system.shutil, "disk_usage", generic_exception)
    assert system.get_free_space_on_disk() is None
    assert len(logs) == 1
    assert in_logs(logs, "Could not get the amount of free space on the filesystem")


def test_get_ram_stats_success(monkeypatch, meminfo, logs):
    """
        Get RAM data, normal conditions
    """
    mock_open = mock.mock_open(read_data=meminfo)
    monkeypatch.setattr(builtins, 'open', mock_open)
    stats = {
        "total": "245724 kB",
        "free": "146968 kB",
        "available": "160988 kB",
    }
    assert system.get_ram_stats() == stats
    assert len(logs) == 0


def test_get_ram_stats_exception(monkeypatch, meminfo, logs):
    """
        Get RAM data, behavior on exception
    """
    def fail_open(*args, **kwargs):
        raise PermissionError()

    monkeypatch.setattr(builtins, 'open', fail_open)
    assert system.get_ram_stats() is None
    assert len(logs) == 1
    assert in_logs(logs, "Could not get RAM data")


def test_report_general_status(monkeypatch):
    """
        Stub test that the status is reported.
    """
    original_system = webcam.system

    class Empty():
        def __getattr__(self, attr):
            return lambda *a, **k: None 

    monkeypatch.setattr(webcam, "system", Empty())
    status = original_system.report_general_status()
    assert "version" in status.keys()
    assert "last reboot" in status.keys()
    assert "uptime" in status.keys()
    assert "hotspot allowed" in status.keys()
    assert "wifi data" in status.keys()
    assert "internet access" in status.keys()
    assert "disk size" in status.keys()
    assert "free disk space" in status.keys()
    assert "RAM" in status.keys()


def test_copy_system_file_success(tmpdir, logs):
    """
        Copy a system file under normal conditions
    """
    pathfrom = tmpdir / "from"
    pathto = tmpdir / "to"
    with open(pathfrom, 'w'):
        pass
    system.copy_system_file(pathfrom, pathto)
    assert os.path.exists(pathfrom)
    assert os.path.exists(pathto)
    assert len(logs) == 0


def test_copy_system_file_exception(tmpdir, logs):
    """
        Copy a system file, behavior under exception
    """
    pathfrom = tmpdir / "from"
    pathto = tmpdir / "to"
    with pytest.raises(RuntimeError):
        system.copy_system_file(pathfrom, pathto)
    assert not os.path.exists(pathto)
    assert len(logs) == 0


def test_give_ownership_to_root_success(tmpdir, logs):
    """
        Chown a file to root under normal conditions
    """
    path = tmpdir / "file"
    with open(path, 'w'):
        pass
    system.give_ownership_to_root(path)
    assert len(logs) == 0


def test_give_ownership_to_root_exception(tmpdir, logs):
    """
        Chown a file to root, behavior under exception
    """
    path = tmpdir / "file"
    with pytest.raises(RuntimeError):
        system.give_ownership_to_root(path)
    assert len(logs) == 0
    

def test_prepare_crontab_string_no_frequency_no_cron(logs):
    """
        Test crontab generation for an empty dict.
        Default frequency is a hour.
    """
    crontab = system.prepare_crontab_string({})
    # range(24) because the last digit is out
    assert crontab == [f"0 {hour} * * *" for hour in range(24)]
    assert len(logs) == 0


def test_prepare_crontab_string_with_frequency_no_cron():
    """
        Test crontab generation for given frequency, nothing else given.
    """
    crontab = system.prepare_crontab_string({
        "frequency": "480",
    })
    assert crontab == ["0 0 * * *", "0 8 * * *", "0 16 * * *"]


def test_prepare_crontab_string_with_frequency_with_cron():
    """
        If frequency is given, crontab values are ignored
    """
    crontab = system.prepare_crontab_string({
        "frequency": "480",
        "minute": "1",
        "hour": "2",
        "day": "3",
        "month": "4",
        "weekday": "5",
    })
    assert crontab == ["0 0 * * *", "0 8 * * *", "0 16 * * *"]


def test_prepare_crontab_string_no_frequency_some_cron(logs):
    """
        Test that crontab does not override frequency
        unless it's explicitly set to 0
    """
    crontab = system.prepare_crontab_string({
        "minute": "1",
        "hour": "2",
        "day": "3",
        "month": "4",
        "weekday": "5",
    })
    # range(24) because the last digit is out
    assert crontab == [f"0 {hour} * * *" for hour in range(24)]
    assert len(logs) == 0


def test_prepare_crontab_string_frequency_zero_some_cron(logs):
    """
        Test that setting the frequency explicitly to 0
        switches to the manual crontab mode even if no
        crontab value is given
    """
    crontab = system.prepare_crontab_string({
        "frequency": "0",
    })
    assert crontab == ["* * * * *"]
    assert len(logs) == 0


def test_prepare_crontab_string_frequency_zero_all_cron(logs):
    """
        Test that crontab does override the frequency
        if it's explicitly set to 0
    """
    crontab = system.prepare_crontab_string({
        "frequency": "0",
        "minute": "1",
        "hour": "2",
        "day": "3",
        "month": "4",
        "weekday": "5",
    })
    assert crontab == ["1 2 3 4 5"]
    assert len(logs) == 0


def test_prepare_crontab_string_frequency_zero_some_cron(logs):
    """
        Test that crontab does override the frequency
        if it's explicitly set to 0. Missing entries default to *
    """
    crontab = system.prepare_crontab_string({
        "frequency": "0",
        "minute": "1",
        "month": "2",
    })
    assert crontab == ["1 * * 2 *"]
    assert len(logs) == 0


def test_prepare_crontab_string_unreadable_frequency(logs):
    """
        Test that a wrong frequency (i.e. a string)
        can be handled gracefully by defaulting.
    """
    crontab = system.prepare_crontab_string({
        "frequency": "wrong!"
    })
    # range(24) because the last digit is out
    assert crontab == [f"{(step%6)*10} {math.floor(step/6)} * * *" 
                        for step in range(24*6)]
    assert len(logs) == 1
    assert in_logs(logs, "frequency cannot be converted into int")


def test_prepare_crontab_string_unreadable_frequency_ignore_cron(logs):
    """
        Test that a wrong frequency (i.e. a string)
        can be handled gracefully by defaulting,
        which means that eventual crontabs are going
        to be ignored
    """
    crontab = system.prepare_crontab_string({
        "frequency": "wrong!",
        "minute": "1",
        "month": "2",
    })
    # range(24) because the last digit is out
    assert crontab == [f"{(step%6)*10} {math.floor(step/6)} * * *" 
                        for step in range(24*6)]
    assert len(logs) == 1
    assert in_logs(logs, "frequency cannot be converted into int")


def test_prepare_crontab_string_affects_frequency(logs):
    """
        Test that start and stop times are considered
        when using the frequency
    """
    crontab = system.prepare_crontab_string({
        "frequency": "480",
        "start_activity": "01:10",
        "stop_activity": "12:23",
    })
    assert crontab == ["10 1 * * *", "10 9 * * *"]
    assert len(logs) == 0


def test_prepare_crontab_string_dont_affect_crontab(logs):
    """
        Test that start and stop times are not considered
        when using the crontab
    """
    crontab = system.prepare_crontab_string({
        "frequency": '0',
        "minute": "*/5",
        "start_activity": "01:00",
        "stop_activity": "12:00",
    })
    assert crontab == ["*/5 * * * *"]
    assert len(logs) == 0


def test_prepare_crontab_string_unreadable_start_time(logs):
    """
        Can handle a wrong start time by defaulting to midnight
    """
    crontab = system.prepare_crontab_string({
        "frequency": "480",
        "start_activity": "wrong time",
        "stop_activity": "12:23",
    })
    assert crontab == ["0 0 * * *", "0 8 * * *"]
    assert len(logs) == 1
    assert in_logs(logs, "Could not read start time")


def test_prepare_crontab_string_unreadable_stop_time(logs):
    """
        Can handle a wrong stop time by defaulting to midnight
    """
    crontab = system.prepare_crontab_string({
        "frequency": "480",
        "start_activity": "12:23",
        "stop_activity": "wrong time",
    })
    assert crontab == ["23 12 * * *", "23 20 * * *"]
    assert len(logs) == 1
    assert in_logs(logs, "Could not read stop time")


def test_prepare_crontab_string_can_fail_1():
    """
        Test that prepare_crontab_string do fail if the data
        is so wrong it's not meant to be written in the
        crontab.
    """
    with pytest.raises(Exception):
        crontab = system.prepare_crontab_string(None)
    

def test_prepare_crontab_string_can_fail_2():
    """
        Test that prepare_crontab_string do fail if the data
        is so wrong it's not meant to be written in the
        crontab.
    """
    with pytest.raises(Exception):
        crontab = system.prepare_crontab_string("wrong!")


def test_prepare_crontab_string_can_fail_3():
    """
        Test that prepare_crontab_string do fail if the data
        is so wrong it's not meant to be written in the
        crontab.
    """
    with pytest.raises(Exception):
        crontab = system.prepare_crontab_string(10)


def test_update_crontab_success(tmpdir, logs):
    """
        Test if the crontab can be updated under normal conditions
    """
    assert webcam.system.CRONJOB_FILE == tmpdir / "zanzocam"
    with open(webcam.system.CRONJOB_FILE, 'w'):
        pass
    system.update_crontab({})
    assert len(logs) == 1
    assert in_logs(logs, "Crontab updated successfully")
    assert open(webcam.system.CRONJOB_FILE, 'r').readlines() == \
        ["# ZANZOCAM - shoot picture\n"] + \
        [f"0 {hour} * * * {constants.SYSTEM_USER} {sys.argv[0]}\n" 
            for hour in range(24)]


def test_update_crontab_prepare_strings_fails(monkeypatch, tmpdir, logs):
    """
        Test that the crontab is unchanged if there is trouble
        decoding the new crontab information 
    """
    assert webcam.system.CRONJOB_FILE == tmpdir / "zanzocam"
    with open(webcam.system.CRONJOB_FILE, 'w') as c:
        c.write("crontab content")

    system.update_crontab(None)  # Will make prepare_crontab_string fail
    assert len(logs) == 1
    assert in_logs(logs, "Something happened assembling the crontab. " \
           "Aborting crontab update.")
    assert open(webcam.system.CRONJOB_FILE, 'r').read() == "crontab content"


def test_update_crontab_backup_fail(tmpdir, logs):
    """
        Test if the crontab can be updated if the backup fails
    """
    assert webcam.system.CRONJOB_FILE == tmpdir / "zanzocam"
    # Backup will fail because there is no file at this path
    system.update_crontab({})
    assert len(logs) == 2
    # Failed backup  
    assert in_logs(logs, "Failed to backup the previous crontab!")
    # Actual crontab replacement
    assert in_logs(logs, "Crontab updated successfully")
    assert open(webcam.system.CRONJOB_FILE, 'r').readlines() == \
        ["# ZANZOCAM - shoot picture\n"] + \
        [f"0 {hour} * * * {constants.SYSTEM_USER} {sys.argv[0]}\n" 
            for hour in range(24)]


def test_update_crontab_write_temp_file_fails(monkeypatch, tmpdir, logs):
    """
        Test that the crontab is unchanged if there is trouble
        writing the temp file. 
    """
    assert webcam.system.CRONJOB_FILE == tmpdir / "zanzocam"
    with open(webcam.system.CRONJOB_FILE, 'w') as c:
        c.write("crontab content")
    # update_crontab uses sys.argv[0], which is always present; but not now...
    monkeypatch.setattr(sys, 'argv', [])

    system.update_crontab({})
    assert len(logs) == 1
    assert in_logs(logs, "Failed to generate the new crontab. " \
           "Aborting crontab update.")
    assert open(webcam.system.CRONJOB_FILE, 'r').read() == \
        "crontab content"


def test_update_crontab_chown_fail(monkeypatch, tmpdir, logs):
    """
        Test that the crontab is unchanged if there is trouble
        overwriting the crontab in /etc/cron.d 
    """
    assert webcam.system.CRONJOB_FILE == tmpdir / "zanzocam"
    with open(webcam.system.CRONJOB_FILE, 'w') as c:
        c.write("crontab content")
    
    def fail(*a, **k):
        raise PermissionError()
    monkeypatch.setattr(webcam.system, "give_ownership_to_root", fail)

    system.update_crontab({})
    assert len(logs) == 1
    assert in_logs(logs, "Failed to assign the correct rights to the " \
           "new crontab file. Aborting crontab update.")
    assert open(webcam.system.CRONJOB_FILE, 'r').read() == \
        "crontab content"


def test_update_crontab_move_fail(monkeypatch, tmpdir, logs):
    """
        Test that the crontab is unchanged if there is trouble
        overwriting the crontab in /etc/cron.d 
    """
    assert webcam.system.CRONJOB_FILE == tmpdir / "zanzocam"
    with open(webcam.system.CRONJOB_FILE, 'w') as c:
        c.write("crontab content")
    
    actually_copy_the_file = webcam.system.copy_system_file

    def fail(*a, **k):
        print(a)
        if a[0] == webcam.system.TEMP_CRONJOB and \
           a[1] == webcam.system.CRONJOB_FILE:
            raise PermissionError()
        else:
            actually_copy_the_file(*a, *k)

    monkeypatch.setattr(webcam.system, "copy_system_file", fail)

    system.update_crontab({})
    assert len(logs) == 1
    assert in_logs(logs, "Failed to replace the old crontab with a new one. " \
           "Aborting crontab update.")
    assert open(webcam.system.CRONJOB_FILE, 'r').read() == \
        "crontab content"


def test_apply_system_settings_success_no_time(logs):
    """
        Check that apply_system_settings updates the crontab.
    """
    with open(webcam.system.CRONJOB_FILE, 'w'):
        pass

    system.apply_system_settings({})
    assert len(logs) == 0
    assert open(webcam.system.CRONJOB_FILE, 'r').readlines() == []


def test_apply_system_settings_success_with_time(logs):
    """
        Check that apply_system_settings updates the crontab.
    """
    with open(webcam.system.CRONJOB_FILE, 'w'):
        pass

    system.apply_system_settings({'time': {}})
    assert in_logs(logs, "Crontab updated successfully")
    assert open(webcam.system.CRONJOB_FILE, 'r').readlines() == \
        ["# ZANZOCAM - shoot picture\n"] + \
        [f"0 {hour} * * * {constants.SYSTEM_USER} {sys.argv[0]}\n" 
            for hour in range(24)]
