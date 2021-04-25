import os
import sys
import stat
import math
import pytest
import requests
import builtins
import subprocess
from pathlib import Path
from unittest import mock
from textwrap import dedent
from freezegun import freeze_time
from datetime import datetime, timedelta

import webcam
import constants
from webcam.configuration import Configuration

from tests.conftest import point_const_to_tmpdir


@pytest.fixture(autouse=True)
def point_to_tmpdir(monkeypatch, tmpdir):
    point_const_to_tmpdir(webcam.configuration, monkeypatch, tmpdir)


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
        "f": {}
    })
    assert decoded == {"a": "a", "b": 2, "c": 3.0, "d": True, 'e': 
                        {"ee": False}, "f": {}}


def test_create_from_dictionary_normal_dict(tmpdir, logs):
    """
        Test that Configuration can be created from a dict,
        and that it will save itself.
    """
    config = Configuration.create_from_dictionary({"a": "hello"}, 
                path = Path(webcam.configuration.CONFIGURATION_FILE))
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
    config = Configuration.create_from_dictionary({}, 
                path = Path(webcam.configuration.CONFIGURATION_FILE))
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
    with pytest.raises(ValueError):
        Configuration(tmpdir)
    with pytest.raises(ValueError):
        Configuration(tmpdir / "i-dont-exist")
    assert len(logs) == 0


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_no_boundaries_given_1(logs):
    """
        If not boundaries are given, they go from 00:00 to 23:59
    """
    config = Configuration.create_from_dictionary({}, 
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    assert config.within_active_hours()
    assert len(logs) == 0


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_no_boundaries_given_2(logs):
    """
        If not boundaries are given, they go from 00:00 to 23:59
    """
    config = Configuration.create_from_dictionary({'time': {}}, 
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    assert config.within_active_hours()
    assert len(logs) == 0


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_only_start_given_1(logs):
    """
        If only start if given, end is midnight
    """
    config = Configuration.create_from_dictionary(
                {'time': {"start_activity": "11:30"}}, 
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    assert config.within_active_hours()
    assert len(logs) == 0


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_only_start_given_1(logs):
    """
        If only start if given, end is midnight
    """
    config = Configuration.create_from_dictionary(
                {'time': {"start_activity": "12:00"}}, 
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    assert config.within_active_hours()
    assert len(logs) == 0


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_only_start_given_3(logs):
    """
        If only start if given, end is midnight
    """
    config = Configuration.create_from_dictionary(
                {'time': {"start_activity": "12:30"}}, 
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    assert not config.within_active_hours()
    assert len(logs) == 0


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_only_stop_given_1(logs):
    """
        If only stop is given, start is midnight
    """
    config = Configuration.create_from_dictionary(
                {'time': {"stop_activity": "11:30"}}, 
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    assert not config.within_active_hours()
    assert len(logs) == 0


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_only_stop_given_2(logs):
    """
        If only stop is given, start is midnight
    """
    config = Configuration.create_from_dictionary(
                {'time': {"stop_activity": "12:00"}}, 
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    assert config.within_active_hours()
    assert len(logs) == 0


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_only_stop_given_3(logs):
    """
        If only stop is given, start is midnight
    """
    config = Configuration.create_from_dictionary(
                {'time': {"stop_activity": "12:30"}}, 
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    assert config.within_active_hours()
    assert len(logs) == 0


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
                }},
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    assert not config.within_active_hours()
    assert len(logs) == 0


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
                }},
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    assert config.within_active_hours()
    assert len(logs) == 0

    
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
                }},
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    assert not config.within_active_hours()
    assert len(logs) == 0

    
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
                }},
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    assert config.within_active_hours()
    assert len(logs) == 0


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_start_and_stop_handle_typos_1(logs):
    """
        Either start or stop is not a valid time
    """
    config = Configuration.create_from_dictionary(
                {'time': {
                    "start_activity": "wrong", 
                }},
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    assert config.within_active_hours()
    assert len(logs) == 1
    assert "Could not read the start-stop time values" in logs[0]['msg']


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_start_and_stop_handle_typos_2(logs):
    """
        Either start or stop is not a valid time
    """
    config = Configuration.create_from_dictionary(
                {'time': {
                    "stop_activity": "wrong", 
                }},
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    assert config.within_active_hours()
    assert len(logs) == 1
    assert "Could not read the start-stop time values" in logs[0]['msg']


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_start_and_stop_handle_typos_3(logs):
    """
        Either start or stop is not a valid time
    """
    config = Configuration.create_from_dictionary(
                {'time': {
                    "start_activity": "23:00", 
                    "stop_activity": "wrong", 
                }},
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    assert config.within_active_hours()
    assert len(logs) == 1
    assert "Could not read the start-stop time values" in logs[0]['msg']


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_start_and_stop_handle_typos_3(logs):
    """
        Either start or stop is not a valid time
    """
    config = Configuration.create_from_dictionary(
                {'time': {
                    "start_activity": "wrong", 
                    "stop_activity": "02:00", 
                }},
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    assert config.within_active_hours()
    assert len(logs) == 1
    assert "Could not read the start-stop time values" in logs[0]['msg']


@freeze_time("2021-01-01 12:00:00")
def test_within_active_hours_start_and_stop_handle_typos_4(logs):
    """
        Either start or stop is not a valid time
    """
    config = Configuration.create_from_dictionary(
                {'time': {
                    "start_activity": "wrong", 
                    "stop_activity": "also wrong", 
                }},
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    assert config.within_active_hours()
    assert len(logs) == 1
    assert "Could not read the start-stop time values" in logs[0]['msg']


def test_backup_success(tmpdir, logs):
    """
        Configuration can backup its own file 
        with a .bak extension
    """
    config = Configuration.create_from_dictionary({},
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    config.backup()
    assert os.path.exists(webcam.configuration.CONFIGURATION_FILE)
    assert os.path.isfile(webcam.configuration.CONFIGURATION_FILE)
    assert os.path.exists(webcam.configuration.CONFIGURATION_FILE + ".bak")
    assert os.path.isfile(webcam.configuration.CONFIGURATION_FILE + ".bak")
    assert len(logs) == 0


def test_backup_fail(tmpdir, logs):
    """
        Configuration can handle a failure during the backup process
    """
    config = Configuration.create_from_dictionary({},
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    os.remove(webcam.configuration.CONFIGURATION_FILE)
    assert not os.path.exists(webcam.configuration.CONFIGURATION_FILE)
    config.backup()
    assert not os.path.exists(webcam.configuration.CONFIGURATION_FILE)
    assert not os.path.exists(webcam.configuration.CONFIGURATION_FILE + ".bak")
    assert len(logs) == 1
    assert "Cannot backup the configuration file" in logs[0]['msg']


def test_restore_backup_success(tmpdir):
    """
        Configuration can restore its backup.
    """
    config = Configuration.create_from_dictionary({},
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    os.remove(webcam.configuration.CONFIGURATION_FILE)
    assert not os.path.exists(webcam.configuration.CONFIGURATION_FILE)
    with open(webcam.configuration.CONFIGURATION_FILE + ".bak", 'w'):
        pass
    config.restore_backup()
    assert os.path.exists(webcam.configuration.CONFIGURATION_FILE)
    assert os.path.isfile(webcam.configuration.CONFIGURATION_FILE)
    assert os.path.exists(webcam.configuration.CONFIGURATION_FILE + ".bak")
    assert os.path.isfile(webcam.configuration.CONFIGURATION_FILE + ".bak")


def test_restore_backup_fail(tmpdir, logs):
    """
        Configuration can restore its backup.
    """
    config = Configuration.create_from_dictionary({},
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    os.remove(webcam.configuration.CONFIGURATION_FILE)
    assert not os.path.exists(webcam.configuration.CONFIGURATION_FILE)
    assert not os.path.exists(webcam.configuration.CONFIGURATION_FILE + ".bak")
    config.restore_backup()
    assert not os.path.exists(webcam.configuration.CONFIGURATION_FILE)
    assert not os.path.exists(webcam.configuration.CONFIGURATION_FILE + ".bak")
    assert len(logs) == 1
    assert "Cannot restore the configuration file from its backup"


def test_overlays_to_download_no_overlays(logs):
    """
        If the overlays block is not present or empty,
        overlays_to_download returns an empty list
    """
    config = Configuration.create_from_dictionary({},
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    assert config.overlays_to_download() == []
    assert len(logs) == 0

    config = Configuration.create_from_dictionary({'overlays': {}},
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    assert config.overlays_to_download() == []
    assert len(logs) == 0


def test_overlays_to_download_wrong_overlays_block(logs):
    """
        If the overlays key dows not contain a dict,
        log the exception and return an empty list
    """
    config = Configuration.create_from_dictionary({'overlays': "wrong!"},
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    assert config.overlays_to_download() == []
    assert len(logs) == 1
    assert "The 'overlays' entry in the configuration file " \
           "does not correspond to a dictionary" in logs[0]['msg']


def test_overlays_to_download_one_overlay_with_path(logs):
    """
        Test with some overlays
    """
    config = Configuration.create_from_dictionary({'overlays': {
                    'top_right': {
                        'path': "image.jpg"
                    }
                }},
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    assert config.overlays_to_download() == ["image.jpg"]
    assert len(logs) == 0


def test_overlays_to_download_one_overlay_with_path_and_other_attrs(logs):
    """
        Test with some overlays
    """
    config = Configuration.create_from_dictionary({'overlays': {
                    'top_right': {
                        'path': "image.jpg",
                        "path2": "wrong.jpg",
                        "text": "shoudln't be here"
                    }
                }},
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    assert config.overlays_to_download() == ["image.jpg"]
    assert len(logs) == 0


def test_overlays_to_download_two_overlays_with_path(logs):
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
                }},
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    assert config.overlays_to_download() == ["image.jpg", 'image2.txt']
    assert len(logs) == 0


def test_overlays_to_download_one_overlay_with_path_one_without(logs):
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
                }},
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    assert config.overlays_to_download() == ["image.jpg"]
    assert len(logs) == 0


def test_overlays_to_download_one_overlay_without_path(logs):
    """
        Test with some overlays
    """
    config = Configuration.create_from_dictionary({'overlays': {
                    'bottom_center': {
                        "text": "hello!"
                    }
                }},
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    assert config.overlays_to_download() == []
    assert len(logs) == 0


def test_overlays_to_download_two_overlays_without_path(logs):
    """
        Test with some overlays
    """
    config = Configuration.create_from_dictionary({'overlays': {
                    'bottom_center': {
                        "text": "hello!"
                    },
                    'top_right': {
                        "text": "image.png"
                    }
                }},
                path = Path(webcam.configuration.CONFIGURATION_FILE))
    assert config.overlays_to_download() == []
    assert len(logs) == 0
