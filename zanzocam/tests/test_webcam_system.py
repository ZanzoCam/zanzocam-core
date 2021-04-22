import os
import sys
import math
import pytest
import requests
import builtins
import subprocess
from unittest import mock
from textwrap import dedent
from freezegun import freeze_time
from datetime import datetime, timedelta

import webcam
import constants
from webcam.system import System

from tests.conftest import point_const_to_tmpdir


@pytest.fixture(autouse=True)
def point_to_tmpdir(monkeypatch, tmpdir):
    point_const_to_tmpdir(webcam.system, monkeypatch, tmpdir)
    # Special extra constants
    webcam.system.CRONJOB_FILE = tmpdir / "zanzocam"


@pytest.fixture
def meminfo():
    yield dedent("""\n
        MemTotal:         245724 kB
        MemFree:          146968 kB
        MemAvailable:     160988 kB
        Buffers:           20764 kB
        Cached:            38232 kB
        SwapCached:         1024 kB
        Active:            57428 kB
        Inactive:          12616 kB
        Active(anon):       9140 kB
        Inactive(anon):     6372 kB
        Active(file):      48288 kB
        Inactive(file):     6244 kB
        Unevictable:          16 kB
        Mlocked:              16 kB
        SwapTotal:        102396 kB
        SwapFree:          61948 kB
        Dirty:                 0 kB
        Writeback:             0 kB
        AnonPages:         10628 kB
        Mapped:            13660 kB
        Shmem:              4464 kB
        KReclaimable:       9084 kB
        Slab:              18772 kB
        SReclaimable:       9084 kB
        SUnreclaim:         9688 kB
        KernelStack:         832 kB
        PageTables:         1732 kB
        NFS_Unstable:          0 kB
        Bounce:                0 kB
        WritebackTmp:          0 kB
        CommitLimit:      225256 kB
        Committed_AS:     348148 kB
        VmallocTotal:     770048 kB
        VmallocUsed:        3352 kB
        VmallocChunk:          0 kB
        Percpu:               64 kB
        CmaTotal:          65536 kB
        CmaFree:           58580 kB
    """)


def test_get_last_reboot_time_success(fake_process, logs):
    """
        Get the last reboot time, test normal behavior
    """
    mock_time = b"2021-01-01 00:00:00"
    fake_process.register_subprocess(
        ['/usr/bin/uptime', '-s'], stdout=mock_time
    )
    last_reboot_time = System.get_last_reboot_time()
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
    last_reboot_time = System.get_last_reboot_time()
    assert last_reboot_time == None
    assert len(logs) == 1
    assert "Could not get last reboot time information" in logs[0]['msg']


@freeze_time("2021-01-01 12:00:00")
def test_get_uptime_success(fake_process, logs):
    """
        Get the uptime, test normal behavior
    """
    mock_time = b"2021-01-01 00:00:00"
    fake_process.register_subprocess(
        ['/usr/bin/uptime', '-s'], stdout=mock_time
    )
    uptime = System.get_uptime()
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
    uptime = System.get_uptime()
    assert uptime == None
    assert len(logs) == 2
    assert "Could not get uptime information" in logs[1]['msg']
    assert "Could not get last reboot time information" in logs[0]['msg']


def test_check_hotspot_allowed_flag_set_to_yes(logs):
    """
        Check if the hotspot is allowed, test YES flag
    """
    with open(constants.HOTSPOT_FLAG, 'w') as f:
        f.write("yes")
    allowed = System.check_hotspot_allowed()
    assert allowed
    assert len(logs) == 0


def test_check_hotspot_allowed_flag_set_to_no(logs):
    """
        Check if the hotspot is allowed, test NO flag
    """
    with open(constants.HOTSPOT_FLAG, 'w') as f:
        f.write("no")
    allowed = System.check_hotspot_allowed()
    assert not allowed
    assert len(logs) == 0 


def test_check_hotspot_allowed_flag_set_to_other(logs):
    """
        Check if the hotspot is allowed, test unexpected flag
    """
    with open(constants.HOTSPOT_FLAG, 'w') as f:
        f.write("Other")
    allowed = System.check_hotspot_allowed()
    assert allowed
    assert len(logs) == 1
    assert "The hostpot flag contains neither YES nor NO" in logs[0]["msg"]


def test_check_hotspot_allowed_permission_error(logs):
    """
        Check if the hotspot is allowed, test permission errors
    """
    with open(constants.HOTSPOT_FLAG, 'w') as f:
        f.write("no")
    os.chmod(constants.HOTSPOT_FLAG, 0o222)
    allowed = System.check_hotspot_allowed()
    assert allowed
    assert len(logs) == 1
    assert "Failed to check if the hotspot is allowed" in logs[0]["msg"]


def test_check_hotspot_allowed_no_file(logs):
    """
        Check if the hotspot is allowed, no file
    """
    assert not os.path.exists(constants.HOTSPOT_FLAG)
    allowed = System.check_hotspot_allowed()
    assert allowed
    assert len(logs) == 1
    assert "Hotspot flag file not found" in logs[0]["msg"]
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
    assert System.run_autohotspot()
    assert len(logs) == 0


def test_run_hotspot_on_wifi_2(fake_process, logs):
    """
        Check if the hotspot runs, turning off hotspot to go on wifi.
    """
    fake_process.register_subprocess(
        ["/usr/bin/sudo", constants.AUTOHOTSPOT_BINARY_PATH], 
        stdout="Hotspot Deactivated, Bringing Wifi Up"
    )
    assert System.run_autohotspot()
    assert len(logs) == 0


def test_run_hotspot_on_wifi_3(fake_process, logs):
    """
        Check if the hotspot runs, connecting to wifi for the first time.
    """
    fake_process.register_subprocess(
        ["/usr/bin/sudo", constants.AUTOHOTSPOT_BINARY_PATH], 
        stdout="Connecting to the WiFi Network"
    )
    assert System.run_autohotspot()
    assert len(logs) == 0


def test_run_hotspot_on_hotspot_1(fake_process, logs):
    """
        Check if the hotspot runs, normal behavior on hotspot
    """
    fake_process.register_subprocess(
        ["/usr/bin/sudo", constants.AUTOHOTSPOT_BINARY_PATH], 
        stdout="Hostspot already active"
    )
    result = System.run_autohotspot()
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
    result = System.run_autohotspot()
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
    result = System.run_autohotspot()
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
    assert System.run_autohotspot() is None
    assert len(logs) == 1
    assert "The hotspot script failed to run" in logs[0]["msg"]


def test_get_wifi_ssid_success(fake_process, logs):
    """
        Check if we can get wifi information under normal conditions
    """
    ssid = "TEST WIFI"
    fake_process.register_subprocess(
        ['/usr/sbin/iwgetid', '-r'], stdout=ssid
    )
    assert System.get_wifi_ssid() == ssid
    assert len(logs) == 0


def test_get_wifi_ssid_no_wifi(fake_process, logs):
    """
        Check if we can get wifi information when the device
        is not connected to any wifi (iwgetid returns nothing)
    """
    fake_process.register_subprocess(
        ['/usr/sbin/iwgetid', '-r'],
    )
    assert System.get_wifi_ssid() == ""
    assert len(logs) == 0


def test_get_wifi_ssid_exception(fake_process, logs):
    """
        Check if we can get wifi information, behavior on exception.
    """
    fake_process.register_subprocess(
        ['/usr/sbin/iwgetid', '-r'], returncode=2
    )
    assert System.get_wifi_ssid() is None
    assert len(logs) == 1
    assert "Could not retrieve WiFi information" in logs[0]["msg"]


def test_check_internet_connectivity_success(monkeypatch, logs):
    """
        Check uplink, normal conditions.
    """
    def alright(url, timeout):
        pass

    monkeypatch.setattr(webcam.system.requests, "head", alright)
    assert System.check_internet_connectivity()
    assert len(logs) == 0


def test_check_internet_connectivity_timeout(monkeypatch, logs):
    """
        Check uplink, request times out.
    """
    def timeout(url, timeout):
        raise requests.ConnectionError()

    monkeypatch.setattr(webcam.system.requests, "head", timeout)
    assert not System.check_internet_connectivity()
    assert len(logs) == 0


def test_check_internet_connectivity_exception(monkeypatch, logs):
    """
        Check uplink, other exception.
    """
    def generic_error(url, timeout):
        raise ValueError()

    monkeypatch.setattr(webcam.system.requests, "head", generic_error)
    assert not System.check_internet_connectivity()
    assert len(logs) == 1
    assert "Could not check if there is Internet access" in logs[0]['msg']


def test_get_filesystem_size_success(monkeypatch, logs):
    """
        Get the filesystem size, normal conditions
    """
    def alright(path):
        return 5*(1024**3), 0, 0

    monkeypatch.setattr(webcam.system.shutil, "disk_usage", alright)
    assert System.get_filesystem_size() == "5.00 GB"
    assert len(logs) == 0


def test_get_filesystem_size_exception(monkeypatch, logs):
    """
        Get the filesystem size, behavior on exception
    """
    def generic_exception(path):
        raise PermissionError()

    monkeypatch.setattr(webcam.system.shutil, "disk_usage", generic_exception)
    assert System.get_filesystem_size() is None
    assert len(logs) == 1
    assert "Could not retrieve the size of the filesystem" in logs[0]['msg']


def test_get_free_space_on_disk_success(monkeypatch, logs):
    """
        Get the amount of free space left, normal conditions
    """
    def alright(path):
        return 0, 0, 900*(1024**2)

    monkeypatch.setattr(webcam.system.shutil, "disk_usage", alright)
    assert System.get_free_space_on_disk() == "900.00 MB"
    assert len(logs) == 0


def test_get_free_space_on_disk_exception(monkeypatch, logs):
    """
        Get the amount of free space left, behavior on exception
    """
    def generic_exception(path):
        raise PermissionError()

    monkeypatch.setattr(webcam.system.shutil, "disk_usage", generic_exception)
    assert System.get_free_space_on_disk() is None
    assert len(logs) == 1
    assert "Could not get the amount of free space on the filesystem" in logs[0]['msg']


def test_get_ram_stats_success(monkeypatch, meminfo, logs):
    """
        Get RAM data, normal conditions
    """
    mock_open = mock.mock_open(read_data=meminfo)
    monkeypatch.setattr(builtins, 'open', mock_open)
    stats = "total: 245724 kB | " + \
            "free: 146968 kB | " + \
            "available: 160988 kB | " + \
            "total swap: 102396 kB | " + \
            "free swap: 61948 kB | "
    assert System.get_ram_stats() == stats
    assert len(logs) == 0


def test_get_ram_stats_exception(monkeypatch, meminfo, logs):
    """
        Get RAM data, behavior on exception
    """
    def fail_open(*args, **kwargs):
        raise PermissionError()

    monkeypatch.setattr(builtins, 'open', fail_open)
    assert System.get_ram_stats() is None
    assert len(logs) == 1
    assert "Could not get RAM data" in logs[0]['msg']


def test_copy_system_file_success(tmpdir, logs):
    """
        Copy a system file under normal conditions
    """
    pathfrom = tmpdir / "from"
    pathto = tmpdir / "to"
    with open(pathfrom, 'w'):
        pass
    assert System.copy_system_file(pathfrom, pathto)
    assert len(logs) == 0


def test_copy_system_file_exception(fake_process, tmpdir, logs):
    """
        Copy a system file, behavior under exception
    """
    pathfrom = tmpdir / "from"
    pathto = tmpdir / "to"
    fake_process.register_subprocess(
        ["/usr/bin/sudo", "cp", str(pathfrom), str(pathto)], returncode=2
    )
    result = System.copy_system_file(pathfrom, pathto)
    assert result is not None
    assert not result
    assert len(logs) == 1
    assert "Something went wrong copying" in logs[0]['msg']


def test_give_ownership_to_root_success(tmpdir, logs):
    """
        Chown a file to root under normal conditions
    """
    path = tmpdir / "file"
    with open(path, 'w'):
        pass
    assert System.give_ownership_to_root(path)
    assert len(logs) == 0


def test_give_ownership_to_root_exception(fake_process, tmpdir, logs):
    """
        Chown a file to root, behavior under exception
    """
    path = tmpdir / "file"
    fake_process.register_subprocess(
        ["/usr/bin/sudo", "chown", "root:root", str(path)], returncode=2
    )
    result = System.give_ownership_to_root(path)
    assert result is not None
    assert not result
    assert len(logs) == 1
    assert "Something went wrong assigning ownership" in logs[0]['msg']


def test_prepare_crontab_string_no_frequency_no_cron(logs):
    """
        Test crontab generation for an empty dict.
        Default frequency is a hour.
    """
    crontab = System.prepare_crontab_string({})
    # range(24) because the last digit is out
    assert crontab == [f"0 {hour} * * *" for hour in range(24)]
    assert len(logs) == 0


def test_prepare_crontab_string_with_frequency_no_cron():
    """
        Test crontab generation for given frequency, nothing else given.
    """
    crontab = System.prepare_crontab_string({
        "frequency": "480",
    })
    assert crontab == ["0 0 * * *", "0 8 * * *", "0 16 * * *"]


def test_prepare_crontab_string_with_frequency_with_cron():
    """
        If frequency is given, crontab values are ignored
    """
    crontab = System.prepare_crontab_string({
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
    crontab = System.prepare_crontab_string({
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
    crontab = System.prepare_crontab_string({
        "frequency": "0",
    })
    assert crontab == ["* * * * *"]
    assert len(logs) == 0


def test_prepare_crontab_string_frequency_zero_all_cron(logs):
    """
        Test that crontab does override the frequency
        if it's explicitly set to 0
    """
    crontab = System.prepare_crontab_string({
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
    crontab = System.prepare_crontab_string({
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
    crontab = System.prepare_crontab_string({
        "frequency": "wrong!"
    })
    # range(24) because the last digit is out
    assert crontab == [f"{(step%6)*10} {math.floor(step/6)} * * *" 
                        for step in range(24*6)]
    assert len(logs) == 1
    assert "frequency cannot be converted into int" in logs[0]['msg']


def test_prepare_crontab_string_unreadable_frequency_ignore_cron(logs):
    """
        Test that a wrong frequency (i.e. a string)
        can be handled gracefully by defaulting,
        which means that eventual crontabs are going
        to be ignored
    """
    crontab = System.prepare_crontab_string({
        "frequency": "wrong!",
        "minute": "1",
        "month": "2",
    })
    # range(24) because the last digit is out
    assert crontab == [f"{(step%6)*10} {math.floor(step/6)} * * *" 
                        for step in range(24*6)]
    assert len(logs) == 1
    assert "frequency cannot be converted into int" in logs[0]['msg']


def test_prepare_crontab_string_affects_frequency(logs):
    """
        Test that start and stop times are considered
        when using the frequency
    """
    crontab = System.prepare_crontab_string({
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
    crontab = System.prepare_crontab_string({
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
    crontab = System.prepare_crontab_string({
        "frequency": "480",
        "start_activity": "wrong time",
        "stop_activity": "12:23",
    })
    assert crontab == ["0 0 * * *", "0 8 * * *"]
    assert len(logs) == 1
    assert "Could not read start time" in logs[0]['msg']


def test_prepare_crontab_string_unreadable_stop_time(logs):
    """
        Can handle a wrong stop time by defaulting to midnight
    """
    crontab = System.prepare_crontab_string({
        "frequency": "480",
        "start_activity": "12:23",
        "stop_activity": "wrong time",
    })
    assert crontab == ["23 12 * * *", "23 20 * * *"]
    assert len(logs) == 1
    assert "Could not read stop time" in logs[0]['msg']


def test_update_crontab_success(tmpdir, logs):
    """
        Test if the crontab can be updated under normal conditions
    """
    assert webcam.system.CRONJOB_FILE == tmpdir / "zanzocam"
    with open(webcam.system.CRONJOB_FILE, 'w'):
        pass
    System.update_crontab({})
    assert len(logs) == 1
    assert "Crontab updated successfully" in logs[0]['msg']
    assert open(webcam.system.CRONJOB_FILE, 'r').readlines() == \
        ["# ZANZOCAM - shoot picture\n"] + \
        [f"0 {hour} * * * {constants.SYSTEM_USER} {sys.argv[0]}\n" 
            for hour in range(24)]

def test_update_crontab_chown_fail(tmpdir, logs):
    assert False