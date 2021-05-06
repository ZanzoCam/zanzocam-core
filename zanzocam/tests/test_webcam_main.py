import os
import pytest
from pathlib import Path
from textwrap import dedent
from freezegun import freeze_time
from datetime import datetime, timedelta

import webcam
import constants
from webcam.main import main
from webcam.system import System
from webcam.errors import ServerError, UnexpectedServerResponse
from webcam.server import Server
from webcam.camera import Camera
from webcam.configuration import Configuration

from tests.conftest import point_const_to_tmpdir, Mock, MockObject


class MockSystem:
    @staticmethod
    def report_general_status():
        return {'test-message':'good'}
    @staticmethod
    def apply_system_settings(settings):
        return


class MockServer:
    def __init__(self, *a, **k):
        self.test_config_data = {"new-test-stuff": "present"}

    def __getattr__(self, *a, **k):
        return lambda *a, **k: None

    def _set_test_configuration(self, config_data):
        self.test_config_data = config_data

    def update_configuration(self, *a, **k):
        return MockObject(self.test_config_data)


class MockCamera:
    def __init__(self, *a, **k):
        pass
    def __getattr__(self, *a, **k):
        return lambda *a, **k: None


class MockConfig(Mock):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)

    def within_active_hours(self):
        return True



@pytest.fixture(autouse=True)
def point_to_tmpdir(monkeypatch, tmpdir):
    modules = [
        webcam.main,
        webcam.system,
        webcam.server.server,
        webcam.server.http_server,
        webcam.server.ftp_server,
        webcam.camera,
        webcam.configuration
    ]
    point_const_to_tmpdir(modules, monkeypatch, tmpdir)


@pytest.fixture()
def mock_modules(monkeypatch):
    monkeypatch.setattr(webcam.main, 'System', MockSystem)
    monkeypatch.setattr(webcam.main, 'Server', MockServer)    
    monkeypatch.setattr(webcam.main, 'Camera', MockCamera)
    monkeypatch.setattr(webcam.main, 'Configuration', MockConfig)

@pytest.fixture()
def mock_modules_apart_config(monkeypatch):
    monkeypatch.setattr(webcam.main, 'System', MockSystem)
    monkeypatch.setattr(webcam.main, 'Server', MockServer)    
    monkeypatch.setattr(webcam.main, 'Camera', MockCamera)


def test_main_no_initial_config_no_backup(mock_modules_apart_config, logs):
    main()
    assert len(logs) > 0
    assert "No configuration file found under" in logs[5]['msg'] 
    assert "Trying to load the backup configuration file" in logs[6]['msg']
    assert "No backup configuration file found" in logs[7]['msg'] 
    assert "Exiting" in logs[7]['msg'] 
    assert "Execution completed with errors" in logs[-2]['msg']


def test_main_unexpected_initial_config_issue(mock_modules_apart_config, logs):
    with open(str(constants.CONFIGURATION_FILE), 'w') as c:
        c.write('not good!')
    main()
    assert len(logs) > 0
    assert "Failed to load the initial configuration" in logs[5]['msg'] 
    assert "Trying to load the backup configuration file" in logs[6]['msg']
    assert "No backup configuration file found" in logs[7]['msg'] 
    assert "Exiting" in logs[7]['msg'] 
    assert "Execution completed with errors" in logs[-2]['msg']


@freeze_time("2021-01-01 10:00:00")
def test_main_no_initial_config_with_backup(mock_modules_apart_config, monkeypatch, logs):
    with open(str(constants.CONFIGURATION_FILE) + ".bak", 'w') as c:
        c.write('{"old-test-stuff": "present"}')

    main()
    assert len(logs) > 0
    assert "No configuration file found under" in logs[5]['msg'] 
    assert "Trying to load the backup configuration file" in logs[6]['msg']
    assert not "Execution completed with errors" in logs[-2]['msg']     


@freeze_time("2021-01-01 10:00:00")
def test_main_out_of_active_hours(mock_modules, monkeypatch, logs):
    monkeypatch.setattr(
        webcam.main.Configuration, 
        'within_active_hours',
        lambda *a, **k: False)

    main()
    assert len(logs) > 0
    assert "The current time is outside active hours. " \
           "Turning off" in logs[6]['msg'] 
    assert "Execution completed successfully" in logs[-2]['msg']


@freeze_time("2021-01-01 10:00:00")
def test_main_error_on_active_hours_check(mock_modules, monkeypatch, logs):
    monkeypatch.setattr(
        webcam.main.Configuration, 
        'within_active_hours',
        lambda *a, **k: 1/0)

    main()
    assert len(logs) > 0
    assert "An error occurred trying to assess if the " \
           "current time is within active hours. " \
           "Assuming YES." in logs[6]['msg']
    assert "Execution completed with errors" in logs[-4]['msg']


@freeze_time("2021-01-01 10:00:00")
def test_main_in_active_hours(mock_modules, monkeypatch, logs):
    main()
    assert len(logs) > 0
    assert "The current time is inside active hours." in logs[6]['msg']
    assert "Execution completed successfully" in logs[-4]['msg']


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
    assert "An error occurred communicating with the server" in logs[7]['msg']
    assert "Restoring the old configuration file" in logs[-7]['msg']
    assert "Execution completed with errors" in logs[-5]['msg']
    new_conf_content = open(webcam.server.server.CONFIGURATION_FILE, 'r').read()
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
    assert "Something unexpected occurred running the main procedure." in logs[7]['msg']
    assert "Restoring the old configuration file" in logs[-7]['msg']
    assert "Execution completed with errors" in logs[-5]['msg']
    new_conf_content = open(webcam.server.server.CONFIGURATION_FILE, 'r').read()
    assert "".join(new_conf_content.split()) == '{"old-test-stuff":"present"}'
    

def test_main_error_fetching_new_config(mock_modules, monkeypatch, logs):
    monkeypatch.setattr(
        webcam.main.Server, 
        'update_configuration',
        lambda *a, **k: 1/0)
    main()
    assert len(logs) > 0
    assert "Downloading the new configuration file" in logs[7]['msg']
    assert "Something went wrong fetching the new configuration " \
           "file from the server. Keeping the old configuration." in logs[8]['msg']
    assert "Configuration in use:" in logs[9]['msg']
    assert "Execution completed with errors" in logs[-4]['msg']