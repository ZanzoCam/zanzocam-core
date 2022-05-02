import os
import pytest
from pathlib import Path
from textwrap import dedent
from freezegun import freeze_time
from datetime import datetime, timedelta

import zanzocam.webcam as webcam
from zanzocam.webcam.configuration import Configuration

from tests.conftest import in_logs


def test_decode_json_values():
    """
        Check how strings from JSON get converted into their Python type
    """
    decoded = Configuration._decode_json_values({
        "a": "a",
        "b": "2",
        "c": "3.0",
        "d": "true",
        "e": {
            "ee": "false"
        },
        "f": {},
        "g#h": 'g#h',
        "i-l-m": 'i-l-m'
    })
    assert decoded == {"a": "a", "b": 2, "c": 3.0, "d": True, 'e': 
                        {"ee": False}, "f": {}, 'g_h': 'g#h', 
                        'i_l_m': 'i-l-m'}


def test_create_from_dictionary_normal_dict(tmpdir, logs):
    """
        Test that Configuration can be created from a dict,
        and that it will save itself.
    """
    config = Configuration.create_from_dictionary({"a": "hello"})
    assert isinstance(config, Configuration)
    assert config.a == "hello"
    assert config._path == Path(webcam.configuration.CONFIGURATION_FILE)
    # Can't take more than a second right?
    assert config._download_time > datetime.now() - timedelta(seconds=1) and \
            config._download_time < datetime.now() + timedelta(seconds=1)
    assert open(webcam.configuration.CONFIGURATION_FILE).read() == \
        dedent("""\
        {
            "a": "hello"
        }""")
    assert len(logs) == 0


def test_create_from_dictionary_empty_dict(tmpdir, logs):
    """
        Test that Configuration can be created from a dict,
        and that it will save itself.
    """
    config = Configuration.create_from_dictionary({})
    assert isinstance(config, Configuration)
    assert config._path == Path(webcam.configuration.CONFIGURATION_FILE)
    # Can't take more than a second right?
    assert config._download_time > datetime.now() - timedelta(seconds=1) and \
            config._download_time < datetime.now() + timedelta(seconds=1)
    assert open(webcam.configuration.CONFIGURATION_FILE).read() == "{}"
    assert len(logs) == 0


def test_init_wrong_path(tmpdir, logs):
    """
        Test that Configuration needs a valid path
    """
    with pytest.raises(FileNotFoundError):
        Configuration(tmpdir)
    with pytest.raises(FileNotFoundError):
        Configuration(tmpdir / "i-dont-exist")
    assert len(logs) == 0


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_no_boundaries_given_1(logs):
    """
        If not boundaries are given, they go from 00:00 to 23:59
    """
    config = Configuration.create_from_dictionary({})
    assert config.within_active_hours()
    assert len(logs) == 2
    assert "Checking" in logs[0]
    assert "inside" in logs[1]


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_no_boundaries_given_2(logs):
    """
        If not boundaries are given, they go from 00:00 to 23:59
    """
    config = Configuration.create_from_dictionary({'time': {}})
    assert config.within_active_hours()
    assert len(logs) == 2
    assert "Checking" in logs[0]
    assert "inside" in logs[1]


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_only_start_given_1(logs):
    """
        If only start if given, end is midnight
    """
    config = Configuration.create_from_dictionary(
        {'time': {"start_activity": "11:30"}})
    assert config.within_active_hours()
    assert len(logs) == 2
    assert "Checking" in logs[0]
    assert "inside" in logs[1]


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_only_start_given_1(logs):
    """
        If only start if given, end is midnight
    """
    config = Configuration.create_from_dictionary(
                {'time': {"start_activity": "12:00"}})
    assert config.within_active_hours()
    assert len(logs) == 2
    assert "Checking" in logs[0]
    assert "inside" in logs[1]


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_only_start_given_3(logs):
    """
        If only start if given, end is midnight
    """
    config = Configuration.create_from_dictionary(
                {'time': {"start_activity": "12:30"}})
    assert not config.within_active_hours()
    assert len(logs) == 2
    assert "Checking" in logs[0]
    assert "outside" in logs[1]


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_only_stop_given_1(logs):
    """
        If only stop is given, start is midnight
    """
    config = Configuration.create_from_dictionary(
                {'time': {"stop_activity": "11:30"}})
    assert not config.within_active_hours()
    assert len(logs) == 2
    assert "Checking" in logs[0]
    assert "outside" in logs[1]


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_only_stop_given_2(logs):
    """
        If only stop is given, start is midnight
    """
    config = Configuration.create_from_dictionary(
                {'time': {"stop_activity": "12:00"}})
    assert config.within_active_hours()
    assert len(logs) == 2
    assert "Checking" in logs[0]
    assert "inside" in logs[1]


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_only_stop_given_3(logs):
    """
        If only stop is given, start is midnight
    """
    config = Configuration.create_from_dictionary(
                {'time': {"stop_activity": "12:30"}})
    assert config.within_active_hours()
    assert len(logs) == 2
    assert "Checking" in logs[0]
    assert "inside" in logs[1]


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_start_and_stop_given_1(logs):
    """
        Both are given, true only if the current time falls 
        inside or on the edges.
    """
    config = Configuration.create_from_dictionary(
                {'time': {
                    "start_activity": "10:30", 
                    "stop_activity": "11:30"
                }})
    assert not config.within_active_hours()
    assert len(logs) == 2
    assert "Checking" in logs[0]
    assert "outside" in logs[1]


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_start_and_stop_given_2(logs):
    """
        Both are given, true only if the current time falls 
        inside or on the edges.
    """
    config = Configuration.create_from_dictionary(
                {'time': {
                    "start_activity": "11:30", 
                    "stop_activity": "12:30"
                }})
    assert config.within_active_hours()
    assert len(logs) == 2
    assert "Checking" in logs[0]
    assert "inside" in logs[1]

    
@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_start_and_stop_given_3(logs):
    """
        Both are given, true only if the current time falls 
        inside or on the edges.
    """
    config = Configuration.create_from_dictionary(
                {'time': {
                    "start_activity": "12:30", 
                    "stop_activity": "13:30"
                }})
    assert not config.within_active_hours()
    assert len(logs) == 2
    assert "Checking" in logs[0]
    assert "outside" in logs[1]

    
@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_start_and_stop_given_4(logs):
    """
        Both are given, true only if the current time falls 
        inside or on the edges.
    """
    config = Configuration.create_from_dictionary(
                {'time': {
                    "start_activity": "12:00", 
                    "stop_activity": "12:00"
                }})
    assert config.within_active_hours()
    assert len(logs) == 2
    assert "Checking" in logs[0]
    assert "inside" in logs[1]


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_start_and_stop_handle_typos_1(logs):
    """
        Either start or stop is not a valid time
    """
    config = Configuration.create_from_dictionary(
                {'time': {
                    "start_activity": "wrong", 
                }})
    assert config.within_active_hours() is None
    assert in_logs(logs, "Could not read the start-stop time values")


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_start_and_stop_handle_typos_2(logs):
    """
        Either start or stop is not a valid time
    """
    config = Configuration.create_from_dictionary(
                {'time': {
                    "stop_activity": "wrong", 
                }})
    assert config.within_active_hours() is None
    assert in_logs(logs, "Could not read the start-stop time values")


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_start_and_stop_handle_typos_3(logs):
    """
        Either start or stop is not a valid time
    """
    config = Configuration.create_from_dictionary(
                {'time': {
                    "start_activity": "23:00", 
                    "stop_activity": "wrong", 
                }})
    assert config.within_active_hours() is None
    assert in_logs(logs, "Could not read the start-stop time values")


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_start_and_stop_handle_typos_4(logs):
    """
        Either start or stop is not a valid time
    """
    config = Configuration.create_from_dictionary(
                {'time': {
                    "start_activity": "wrong", 
                    "stop_activity": "02:00", 
                }})
    assert config.within_active_hours() is None
    assert in_logs(logs, "Could not read the start-stop time values")


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_start_and_stop_handle_typos_5(logs):
    """
        Either start or stop is not a valid time
    """
    config = Configuration.create_from_dictionary(
                {'time': {
                    "start_activity": "wrong", 
                    "stop_activity": "also wrong", 
                }})
    assert config.within_active_hours() is None
    assert in_logs(logs, "Could not read the start-stop time values")


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_unexpected_exception(logs, monkeypatch):
    """
        Either start or stop is not a valid time
    """
    monkeypatch.setattr(
        webcam.configuration.Configuration,
        "get_stop_time", 
        lambda *a, **k: int("a")
    )
    config = Configuration.create_from_dictionary({})
    assert config.within_active_hours() is None
    assert in_logs(logs, "Could not read the start-stop time values")


def test_backup_success(tmpdir, logs):
    """
        Configuration can backup its own file 
        with a .bak extension
    """
    config = Configuration.create_from_dictionary({})
    assert os.path.isfile(webcam.configuration.CONFIGURATION_FILE)
    assert not os.path.exists(
        str(webcam.configuration.CONFIGURATION_FILE) + ".bak")
    config.backup()
    assert os.path.isfile(webcam.configuration.CONFIGURATION_FILE)
    assert os.path.isfile(
        str(webcam.configuration.CONFIGURATION_FILE) + ".bak")
    assert open(webcam.configuration.CONFIGURATION_FILE).read() == \
        open(str(webcam.configuration.CONFIGURATION_FILE) + ".bak").read()
    assert len(logs) == 0


def test_backup_fail(tmpdir, logs):
    """
        Configuration can handle a failure during the backup process
    """
    config = Configuration.create_from_dictionary({})
    
    backup_path = str(webcam.configuration.CONFIGURATION_FILE) + ".bak"
    with open(backup_path, 'w'):
        pass
    os.chmod(backup_path, 0o444)

    config.backup()
    assert open(webcam.configuration.CONFIGURATION_FILE).read() != \
        open(backup_path).read()
    assert len(logs) == 1
    assert in_logs(logs, "Cannot backup the configuration file")


def test_restore_backup_success(tmpdir):
    """
        Configuration can restore its backup.
    """
    config = Configuration.create_from_dictionary({})
    os.remove(webcam.configuration.CONFIGURATION_FILE)
    
    backup_path = str(webcam.configuration.CONFIGURATION_FILE) + ".bak"
    assert not os.path.exists(webcam.configuration.CONFIGURATION_FILE)
    with open(backup_path, 'w'):
        pass

    config.restore_backup()
    
    assert os.path.isfile(webcam.configuration.CONFIGURATION_FILE)
    assert os.path.isfile(backup_path)
    assert open(webcam.configuration.CONFIGURATION_FILE).read() == \
        open(backup_path).read()


def test_restore_backup_fail(tmpdir, logs):
    """
        Configuration can restore its backup.
    """
    config = Configuration.create_from_dictionary({})
    os.remove(webcam.configuration.CONFIGURATION_FILE)

    backup_path = str(webcam.configuration.CONFIGURATION_FILE) + ".bak"
    with open(backup_path, 'w'):
        pass
    os.chmod(backup_path, 0o222)

    config.restore_backup()
    assert not os.path.exists(webcam.configuration.CONFIGURATION_FILE)
    assert os.path.exists(backup_path)
    assert len(logs) == 1
    assert "Cannot restore the configuration file from its backup"


def test_list_overlays_no_overlays(logs):
    """
        If the overlays block is not present or empty,
        list_overlays returns an empty list
    """
    config = Configuration.create_from_dictionary({})
    assert config.list_overlays() == []
    assert len(logs) == 1

    config = Configuration.create_from_dictionary({'overlays': {}},
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    assert config.list_overlays() == []
    assert len(logs) == 2


def test_list_overlays_wrong_overlays_block(logs):
    """
        If the overlays key dows not contain a dict,
        log the exception and return an empty list
    """
    config = Configuration.create_from_dictionary({'overlays': "wrong!"})
    assert config.list_overlays() == []
    assert len(logs) == 2
    assert in_logs(logs, "dictionary")


def test_list_overlays_one_overlay_with_path(logs):
    """
        Test with some overlays
    """
    config = Configuration.create_from_dictionary({'overlays': {
                    'top_right': {
                        'path': "image.jpg"
                    }
                }})
    assert config.list_overlays() == ["image.jpg"]
    assert len(logs) == 2


def test_list_overlays_one_overlay_with_path_and_other_attrs(logs):
    """
        Test with some overlays
    """
    config = Configuration.create_from_dictionary({'overlays': {
                    'top_right': {
                        'path': "image.jpg",
                        "path2": "wrong.jpg",
                        "text": "shouldn't be here"
                    }
                }})
    assert config.list_overlays() == ["image.jpg"]
    assert len(logs) == 2


def test_list_overlays_two_overlays_with_path(logs):
    """
        Test with some overlays
    """
    config = Configuration.create_from_dictionary({'overlays': {
                    'top_right': {
                        'path': "image.jpg"
                    },
                    'bottom_center': {
                        "path": "image2.txt"  # extension not checked
                    }
                }})
    assert config.list_overlays() == ["image.jpg", 'image2.txt']
    assert len(logs) == 3


def test_list_overlays_one_overlay_with_path_one_without(logs):
    """
        Test with some overlays
    """
    config = Configuration.create_from_dictionary({'overlays': {
                    'top_right': {
                        'path': "image.jpg"
                    },
                    'bottom_center': {
                        "text": "hello!"
                    }
                }})
    assert config.list_overlays() == ["image.jpg"]
    assert len(logs) == 2


def test_list_overlays_one_overlay_without_path(logs):
    """
        Test with some overlays
    """
    config = Configuration.create_from_dictionary({'overlays': {
                    'bottom_center': {
                        "text": "hello!",
                        "peth": "wrong.gif"
                    }
                }})
    assert config.list_overlays() == []
    assert len(logs) == 1


def test_list_overlays_two_overlays_without_path(logs):
    """
        Test with some overlays
    """
    config = Configuration.create_from_dictionary({'overlays': {
                    'bottom_center': {
                        "text": "hello!"
                    },
                    'top_right': {
                        "path2": "image.png"
                    }
                }})
    assert config.list_overlays() == []
    assert len(logs) == 1
