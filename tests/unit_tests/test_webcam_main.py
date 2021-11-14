import os
import json
import pytest
from pathlib import Path
from unittest import mock
from textwrap import dedent
from freezegun import freeze_time
from datetime import datetime, timedelta

import zanzocam.webcam as webcam
import zanzocam.constants as constants
from zanzocam.webcam.utils import log
from zanzocam.webcam.main import main
from zanzocam.webcam.system import System
from zanzocam.webcam.errors import ServerError
from zanzocam.webcam.server import Server
from zanzocam.webcam.camera import Camera
from zanzocam.webcam.configuration import Configuration

from tests.conftest import in_logs


def test_main_fail_status_check(mock_modules_apart_config, monkeypatch, logs):
    with open(str(constants.CONFIGURATION_FILE), 'w') as c:
        c.write('{"old-test-stuff": "present"}')

    monkeypatch.setattr(
        webcam.main.System, 
        'report_general_status',
        lambda *a, **k: 1/0)

    main()
    assert len(logs) > 0
    assert in_logs(logs, "Something unexpected happened during the system "
                         "status check.")
    assert in_logs(logs, "Execution completed with errors")


def test_main_fail_locale_setting(mock_modules_apart_config, monkeypatch, logs):
    with open(str(constants.CONFIGURATION_FILE), 'w') as c:
        c.write('{"old-test-stuff": "present"}')

    monkeypatch.setattr(
        webcam.main.locale, 
        'setlocale',
        lambda *a, **k: 1/0)

    main()
    assert len(logs) > 0
    assert in_logs(logs, "Could not set locale")
    assert in_logs(logs, "Execution completed with errors")


def test_main_no_initial_config_no_backup(mock_modules_apart_config, logs):
    main()
    assert len(logs) > 0
    assert in_logs(logs, "No configuration file found under") 
    assert in_logs(logs, "Trying to load the backup configuration file")
    assert in_logs(logs, "No backup configuration file found") 
    assert in_logs(logs, "Exiting") 
    assert in_logs(logs, "Execution completed with errors")

def test_main_no_initial_config_bad_backup(mock_modules_apart_config, logs):
    with open(str(constants.CONFIGURATION_FILE) + ".bak", 'w') as c:
        c.write('Not JSON!')

    main()
    assert len(logs) > 0
    assert in_logs(logs, "No configuration file found under") 
    assert in_logs(logs, "Trying to load the backup configuration file")
    assert in_logs(logs, "Failed to load the backup configuration") 
    assert in_logs(logs, "Exiting") 
    assert in_logs(logs, "Execution completed with errors")


def test_main_unexpected_initial_config_issue(mock_modules_apart_config, logs):
    with open(str(constants.CONFIGURATION_FILE), 'w') as c:
        c.write('not good!')
    main()
    assert len(logs) > 0
    assert in_logs(logs, "Failed to load the initial configuration") 
    assert in_logs(logs, "Trying to load the backup configuration file")
    assert in_logs(logs, "No backup configuration file found") 
    assert in_logs(logs, "Exiting") 
    assert in_logs(logs, "Execution completed with errors")


@freeze_time("2021-01-01 10:00:00")
def test_main_no_initial_config_with_backup(mock_modules_apart_config, monkeypatch, logs):
    with open(str(constants.CONFIGURATION_FILE) + ".bak", 'w') as c:
        c.write('{"old-test-stuff": "present"}')

    main()
    assert len(logs) > 0
    assert in_logs(logs, "No configuration file found under") 
    assert in_logs(logs, "Trying to load the backup configuration file")
    assert not in_logs(logs, "Execution completed with errors")


@freeze_time("2021-01-01 10:00:00")
def test_main_out_of_active_hours(mock_modules, monkeypatch, logs):
    monkeypatch.setattr(
        webcam.main.Configuration, 
        'within_active_hours',
        lambda *a, **k: False)

    main()
    assert len(logs) > 0
    assert in_logs(logs, "The current time is outside active hours. " \
           "Turning off")
    assert in_logs(logs, "Execution completed successfully")


@freeze_time("2021-01-01 10:00:00")
def test_main_error_on_active_hours_check(mock_modules, monkeypatch, logs):
    monkeypatch.setattr(
        webcam.main.Configuration, 
        'within_active_hours',
        lambda *a, **k: 1/0)

    main()
    assert len(logs) > 0
    assert in_logs(logs, "An error occurred trying to assess if the " \
           "current time is within active hours. " \
           "Assuming YES.")
    assert in_logs(logs, "Execution completed with errors")


@freeze_time("2021-01-01 10:00:00")
def test_main_in_active_hours(mock_modules, monkeypatch, logs):
    main()
    assert len(logs) > 0
    assert in_logs(logs, "The current time is inside active hours.")
    assert in_logs(logs, "Execution completed successfully")


def test_main_error_creating_server_servererror(mock_modules_apart_config, monkeypatch, logs):
    with open(str(constants.CONFIGURATION_FILE) + ".bak", 'w') as c:
            c.write('{"old-test-stuff": "present"}')

    with open(str(constants.CONFIGURATION_FILE), 'w') as c:
        c.write('{"new-test-stuff": "present"}')

    def raise_servererror(*a, **k):
        raise ServerError('test error')

    monkeypatch.setattr(
        webcam.main.Server, 
        '__init__', raise_servererror)

    main()
    assert len(logs) > 0
    assert in_logs(logs, "An error occurred communicating with the server")
    assert in_logs(logs, "Restoring the old configuration file")
    assert in_logs(logs, "Execution completed with errors")
    new_conf_content = open(constants.CONFIGURATION_FILE, 'r').read()
    assert "".join(new_conf_content.split()) == '{"old-test-stuff":"present"}'


def test_main_error_creating_server_exception(mock_modules_apart_config, monkeypatch, logs):
    with open(str(constants.CONFIGURATION_FILE) + ".bak", 'w') as c:
            c.write('{"old-test-stuff": "present"}')
    with open(str(constants.CONFIGURATION_FILE), 'w') as c:
        c.write('{"new-test-stuff": "present"}')

    monkeypatch.setattr(
        webcam.main.Server, 
        '__init__',
        lambda *a, **k: 1/0)

    main()
    assert len(logs) > 0
    assert in_logs(logs, "Something unexpected occurred running the main procedure.")
    assert in_logs(logs, "Restoring the old configuration file")
    assert in_logs(logs, "Execution completed with errors")
    new_conf_content = open(constants.CONFIGURATION_FILE, 'r').read()
    assert "".join(new_conf_content.split()) == '{"old-test-stuff":"present"}'
    

def test_main_error_fetching_new_config(mock_modules_apart_config, monkeypatch, logs):
    with open(str(constants.CONFIGURATION_FILE) + ".bak", 'w') as c:
        c.write('{"server": {"old-test-stuff": "present"}}')
    
    with open(str(constants.CONFIGURATION_FILE), 'w') as c:
        c.write('{"server": {"new-test-stuff": "present"}}')

    monkeypatch.setattr(
        webcam.main.Server, 
        'update_configuration',
        lambda *a, **k: 1/0)

    main()
    assert len(logs) > 0
    assert in_logs(logs, "Downloading the new configuration file")
    assert in_logs(logs, "Something went wrong fetching the new configuration " \
           "file from the server. Keeping the old configuration.")
    assert in_logs(logs, "Configuration in use:")
    assert in_logs(logs, "new_test_stuff")
    assert in_logs(logs, "Restoring the old configuration file.")
    assert in_logs(logs, "The next run will use the following server configuration")
    assert in_logs(logs, "old_test_stuff")
    assert in_logs(logs, "Execution completed with errors")
    assert in_logs(logs, "Sending failure report")
    assert in_logs(logs, "Failure report uploaded successfully")

def test_main_no_overlays_at_all(mock_modules_apart_config, monkeypatch, logs):
    with open(str(constants.CONFIGURATION_FILE), 'w') as c:
        c.write('{"server": {"old-test-config": "present"}}')

    monkeypatch.setattr(
        webcam.main.Server, 
        'update_configuration',
        lambda *a, **k: Configuration.create_from_dictionary(
            {"server": {"new-test-config": "present"}}))

    main()
    assert len(logs) > 0
    assert not in_logs(logs, "old_test_config")
    assert in_logs(logs, "new_test_config")
    assert in_logs(logs, "Overlays to download: []")
    assert in_logs(logs, "Execution completed successfully")


def test_main_overlays_block_empty(mock_modules_apart_config, monkeypatch, logs):
    with open(str(constants.CONFIGURATION_FILE), 'w') as c:
        c.write('{"server": {"old-test-config": "present"}, "overlays": {}}')

    monkeypatch.setattr(
        webcam.main.Server, 
        'update_configuration',
        lambda *a, **k: Configuration.create_from_dictionary(
            {"server": {"new-test-config": "present"}, "overlays": {}}))

    main()
    assert len(logs) > 0
    assert not in_logs(logs, "old_test_config")
    assert in_logs(logs, "new_test_config")
    assert in_logs(logs, "Overlays to download: []")
    assert in_logs(logs, "Execution completed successfully")


def test_main_no_overlays_to_download(mock_modules_apart_config, monkeypatch, logs):
    with open(str(constants.CONFIGURATION_FILE), 'w') as c:
        c.write('{"server": {"old-test-config": "present"}}')

    monkeypatch.setattr(
        webcam.main.Server, 
        'update_configuration',
        lambda *a, **k: Configuration.create_from_dictionary(
            {"server": {"new-test-config": "present"},
             "overlays": {"top_right": {"attribute": "something"}}}))

    main()
    assert len(logs) > 0
    assert not in_logs(logs, "old_test_config")
    assert in_logs(logs, "new_test_config")
    assert in_logs(logs, "Overlays to download: []")
    assert in_logs(logs, "Execution completed successfully")


def test_main_some_overlays_to_download(mock_modules_apart_config, monkeypatch, logs):
    with open(str(constants.CONFIGURATION_FILE), 'w') as c:
        c.write('{"server": {"old-test-config": "present"}}')

    monkeypatch.setattr(
        webcam.main.Server, 
        'update_configuration',
        lambda *a, **k: Configuration.create_from_dictionary(
            {"server": {"new-test-config": "present"},
             "overlays": {
                "top_right": {"path": "overlay1.jpg"},
                "top_left": {"path": "overlay2.jpg"},
            }}))

    main()
    assert len(logs) > 0
    assert not in_logs(logs, "old_test_config")
    assert in_logs(logs, "new_test_config")
    assert in_logs(logs, "Overlays to download: ['overlay1.jpg', 'overlay2.jpg']")
    assert in_logs(logs, "Downloading overlay images from")
    assert in_logs(logs, "Execution completed successfully")


def test_main_fail_to_download_overlays(mock_modules_apart_config, monkeypatch, logs):
    with open(str(constants.CONFIGURATION_FILE), 'w') as c:
        c.write('{"server": {"old-test-config": "present"}}')

    monkeypatch.setattr(
        webcam.main.Server, 
        'update_configuration',
        lambda *a, **k: Configuration.create_from_dictionary(
            {"server": {"new-test-config": "present"},
             "overlays": {
                "top_right": {"path": "overlay1.jpg"},
                "top_left": {"path": "overlay2.jpg"},
            }}))

    webcam.main.Server.download_overlay_images = lambda *a, **k: 1/0

    main()
    assert len(logs) > 0
    assert not in_logs(logs, "old_test_config")
    assert in_logs(logs, "new_test_config")
    assert in_logs(logs, "Overlays to download: ['overlay1.jpg', 'overlay2.jpg']")
    assert in_logs(logs, "Downloading overlay images from")
    assert in_logs(logs, "Something went wrong fetching the new overlay "
                         "images from the server. Ignoring them.")
    assert in_logs(logs, "Uploading picture to")
    assert not in_logs(logs, "Restoring the old configuration file.")
    assert in_logs(logs, "Execution completed with errors")


def test_main_no_change_in_system_settings(mock_modules_apart_config, monkeypatch, logs):
    with open(str(constants.CONFIGURATION_FILE), 'w') as c:
        c.write('{"server": {"old-test-config": "present"}}')

    monkeypatch.setattr(
        webcam.main.Server, 
        'update_configuration',
        lambda *a, **k: Configuration.create_from_dictionary(
            {"server": {"new-test-config": "present"}}))

    main()
    assert len(logs) > 0
    assert not in_logs(logs, "old_test_config")
    assert in_logs(logs, "new_test_config")
    assert not in_logs(logs, "Applying new system settings")
    assert in_logs(logs, "System settings didn't change")
    assert in_logs(logs, "Execution completed successfully")


def test_main_some_change_in_system_settings(mock_modules_apart_config, monkeypatch, logs):
    with open(str(constants.CONFIGURATION_FILE), 'w') as c:
        c.write('{"server": {"old-test-config": "present"}}')

    monkeypatch.setattr(
        webcam.main.Server, 
        'update_configuration',
        lambda *a, **k: Configuration.create_from_dictionary({
            "server": {"new-test-config": "present"},
            "time": {"frequency": "10"}
            })
    )
    main()
    assert len(logs) > 0
    assert not in_logs(logs, "old_test_config")
    assert in_logs(logs, "new_test_config")
    assert in_logs(logs, "Applying new system settings")
    assert not in_logs(logs, "System settings didn't change")
    assert in_logs(logs, "Execution completed successfully")


def test_main_error_applying_system_settings(mock_modules_apart_config, monkeypatch, logs):
    with open(str(constants.CONFIGURATION_FILE), 'w') as c:
        c.write('{"server": {"old-test-config": "present"}, "time": {"frequency": "120"}}')

    monkeypatch.setattr(
        webcam.main.Server, 
        'update_configuration',
        lambda *a, **k: Configuration.create_from_dictionary({
            "server": {"new-test-config": "present"},
            "time": {"frequency": "10"}
            })
    )
    monkeypatch.setattr(
        webcam.main.System, 
        'apply_system_settings',
        lambda *a, **k: 1/0
    )
    main()
    assert len(logs) > 0
    assert not in_logs(logs, "old_test_config")
    assert in_logs(logs, "new_test_config")
    assert in_logs(logs, "Applying new system settings")
    assert not in_logs(logs, "System settings didn't change")
    assert in_logs(logs, "Something happened while applying the system " \
                         "settings from the new configuration file.")
    assert in_logs(logs, '"frequency": 120')
    assert in_logs(logs, "Execution completed with errors")


def test_main_error_taking_picture(mock_modules_apart_config, monkeypatch, logs):
    with open(str(constants.CONFIGURATION_FILE), 'w') as c:
        c.write('{"server": {"old-test-config": "present"}}')

    monkeypatch.setattr(
        webcam.main.Server, 
        'update_configuration',
        lambda *a, **k: Configuration.create_from_dictionary({
            "server": {"new-test-config": "present"}
            })
    )
    monkeypatch.setattr(
        webcam.main.Camera, 
        'take_picture',
        lambda *a, **k: 1/0
    )
    main()
    assert len(logs) > 0
    assert not in_logs(logs, "old_test_config")
    assert in_logs(logs, "new_test_config")
    assert in_logs(logs, "An error occurred while taking the picture.")
    assert in_logs(logs, "trying again.")
    assert in_logs(logs, "Something happened at the second attempt too!")
    assert in_logs(logs, "Exiting")
    assert in_logs(logs, "Cleaning up image files")
    assert not in_logs(logs, "Failed to clean up image files")
    assert not in_logs(logs, "Restoring the old configuration file")
    assert in_logs(logs, "Execution completed with errors")


def test_main_error_taking_picture_only_first_time(mock_modules_apart_config, monkeypatch, logs):
    with open(str(constants.CONFIGURATION_FILE), 'w') as c:
        c.write('{"server": {"old-test-config": "present"}}')

    monkeypatch.setattr(
        webcam.main.Server, 
        'update_configuration',
        lambda *a, **k: Configuration.create_from_dictionary({
            "server": {"new-test-config": "present"}
        })
    )
    monkeypatch.setattr(
        webcam.main.Camera, 
        "take_picture", 
        mock.Mock(side_effect=[Exception('test exception'), None])
    )
    main()
    assert len(logs) > 0
    assert not in_logs(logs, "old_test_config")
    assert in_logs(logs, "new_test_config")
    assert in_logs(logs, "An error occurred while taking the picture.")
    assert in_logs(logs, "trying again.")
    assert not in_logs(logs, "Something happened at the second attempt too!")
    assert in_logs(logs, "Uploading picture to")
    assert in_logs(logs, "Cleaning up image files")
    assert not in_logs(logs, "Failed to clean up image files")
    assert not in_logs(logs, "Restoring the old configuration file")
    assert in_logs(logs, "Execution completed with errors")


def test_main_error_uploading_picture(mock_modules_apart_config, monkeypatch, logs):
    with open(str(constants.CONFIGURATION_FILE), 'w') as c:
        c.write('{"server": {"old-test-config": "present"}}')

    monkeypatch.setattr(
        webcam.main.Server, 
        'update_configuration',
        lambda *a, **k: Configuration.create_from_dictionary({
            "server": {"new-test-config": "present"}
        })
    )
    monkeypatch.setattr(
        webcam.main.Server, 
        'upload_picture',
        lambda *a, **k: 1/0
    )
    main()
    assert len(logs) > 0
    assert not in_logs(logs, "old_test_config")
    assert in_logs(logs, "new_test_config")
    assert in_logs(logs, "Something happened uploading the picture")
    assert in_logs(logs, "The picture won't be uploaded")
    assert in_logs(logs, "Cleaning up image files")
    assert in_logs(logs, "Restoring the old configuration file")
    assert in_logs(logs, "Execution completed with errors")


def test_main_fail_cleanup_image_files(mock_modules_apart_config, monkeypatch, logs):
    with open(str(constants.CONFIGURATION_FILE), 'w') as c:
        c.write('{"server": {"old-test-config": "present"}}')

    monkeypatch.setattr(
        webcam.main.Server,
        'update_configuration',
        lambda *a, **k: Configuration.create_from_dictionary({
            "server": {"new-test-config": "present"}
        })
    )
    monkeypatch.setattr(
        webcam.main.Camera, 
        'cleanup_image_files',
        lambda *a, **k: 1/0
    )
    main()
    assert len(logs) > 0
    assert not in_logs(logs, "old_test_config")
    assert in_logs(logs, "new_test_config")
    assert in_logs(logs, "Cleaning up image files")
    assert in_logs(logs, "Failed to clean up image files")
    assert not in_logs(logs, "Restoring the old configuration file")
    assert in_logs(logs, "Execution completed with errors")


def test_main_fail_upload_logs_no_failure_report_needed(mock_modules_apart_config, monkeypatch, logs):
    with open(str(constants.CONFIGURATION_FILE), 'w') as c:
        c.write('{"server": {"old-test-config": "present"}}')

    monkeypatch.setattr(
        webcam.main.Server,
        'update_configuration',
        lambda *a, **k: Configuration.create_from_dictionary({
            "server": {"new-test-config": "present"}
        })
    )
    monkeypatch.setattr(
        webcam.main.Server,
        'upload_logs',
        lambda *a, **k: 1/0
    )
    main()
    assert len(logs) > 0
    assert not in_logs(logs, "old_test_config")
    assert in_logs(logs, "new_test_config")
    assert in_logs(logs, "Execution completed successfully")
    assert not in_logs(logs, "Sending failure report to")
    assert in_logs(logs, "Something happened while uploading the logs")
    assert in_logs(logs, "Logs won't be uploaded")


def test_main_fail_upload_failure_report(mock_modules_apart_config, monkeypatch, logs):
    with open(str(constants.CONFIGURATION_FILE) + ".bak", 'w') as c:
        c.write('{"server": {"old-test-stuff": "present"}}')
    
    with open(str(constants.CONFIGURATION_FILE), 'w') as c:
        c.write('{"server": {"new-test-stuff": "present"}}')

    monkeypatch.setattr(
        webcam.main.Server, 
        'update_configuration',
        lambda *a, **k: 1/0)
    monkeypatch.setattr(
        webcam.main.Server, 
        'upload_failure_report',
        lambda *a, **k: 1/0)

    main()
    assert len(logs) > 0
    assert in_logs(logs, "Downloading the new configuration file")
    assert in_logs(logs, "Something went wrong fetching the new configuration " \
           "file from the server. Keeping the old configuration.")
    assert in_logs(logs, "Configuration in use:")
    assert in_logs(logs, "new_test_stuff")
    assert in_logs(logs, "Restoring the old configuration file.")
    assert in_logs(logs, "The next run will use the following server configuration")
    assert in_logs(logs, "old_test_stuff")
    assert in_logs(logs, "Execution completed with errors")
    assert in_logs(logs, "Sending failure report")
    assert in_logs(logs, "Something happened while uploading the failure report")
    assert in_logs(logs, "The report won't be uploaded")
    assert not in_logs(logs, "Failure report uploaded successfully")
