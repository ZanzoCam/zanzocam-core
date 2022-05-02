from unittest import mock
from freezegun import freeze_time

import zanzocam.webcam as webcam
import zanzocam.constants as constants
from zanzocam.webcam.main import main
from zanzocam.webcam.errors import ServerError
from zanzocam.webcam.configuration import Configuration

from tests.conftest import in_logs



def test_main_no_initial_config_no_backup(mock_modules_apart_config, logs):
    main()
    assert len(logs) > 0
    assert in_logs(logs, "No configuration file found under") 
    assert in_logs(logs, "Trying to load backup configuration")
    assert in_logs(logs, "No backup configuration found") 
    assert in_logs(logs, "Exiting") 
    assert in_logs(logs, "Execution completed with errors")

def test_main_no_initial_config_bad_backup(mock_modules_apart_config, logs):
    with open(str(constants.CONFIGURATION_FILE) + ".bak", 'w') as c:
        c.write('Not JSON!')

    main()
    assert len(logs) > 0
    assert in_logs(logs, "No configuration file found under") 
    assert in_logs(logs, "Trying to load backup configuration")
    assert in_logs(logs, "Failed to load the backup configuration") 
    assert in_logs(logs, "Exiting") 
    assert in_logs(logs, "Execution completed with errors")


def test_main_unexpected_initial_config_issue(mock_modules_apart_config, logs):
    with open(str(constants.CONFIGURATION_FILE), 'w') as c:
        c.write('not good!')
    main()
    assert len(logs) > 0
    assert in_logs(logs, "Failed to load configuration") 
    assert in_logs(logs, "Trying to load backup configuration")
    assert in_logs(logs, "No backup configuration found") 
    assert in_logs(logs, "Exiting") 
    assert in_logs(logs, "Execution completed with errors")


@freeze_time("2021-01-01 10:00:00")
def test_main_no_initial_config_with_backup(mock_modules_apart_config, monkeypatch, logs):
    with open(str(constants.CONFIGURATION_FILE) + ".bak", 'w') as c:
        c.write('{"old-test-stuff": "present"}')

    main()
    assert len(logs) > 0
    assert in_logs(logs, "No configuration file found under") 
    assert in_logs(logs, "Trying to load backup configuration")
    assert in_logs(logs, "Execution completed successfully")


@freeze_time("2021-01-01 10:00:00")
def test_main_out_of_active_hours(mock_modules, monkeypatch, logs):
    monkeypatch.setattr(
        webcam.configuration.Configuration,
        'within_active_hours',
        lambda *a, **k: False)

    with open(str(constants.CONFIGURATION_FILE), 'w') as c:
        c.write('{"something": "present"}')

    main()
    assert len(logs) > 0
    assert in_logs(logs, "Turning off")
    assert in_logs(logs, "Execution completed successfully")


@freeze_time("2021-01-01 10:00:00")
def test_main_in_active_hours(mock_modules, monkeypatch, logs):
    with open(str(constants.CONFIGURATION_FILE), 'w') as c:
        c.write('{"something": "present"}')

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
    assert in_logs(logs, "Scanning the configuration for overlays")
    assert in_logs(logs, "Execution completed successfully")


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
        "take_picture", 
        lambda *a, **k: 1/0
    )
    main()
    assert len(logs) > 0
    assert not in_logs(logs, "old_test_config")
    assert in_logs(logs, "new_test_config")
    assert in_logs(logs, "An exception occurred!")
    assert in_logs(logs, "retrying")
    assert not in_logs(logs, "Restoring the old configuration")
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
    assert in_logs(logs, "Execution completed with errors")
