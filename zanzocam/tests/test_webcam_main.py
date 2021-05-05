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
from webcam.server import Server
from webcam.camera import Camera
from webcam.configuration import Configuration

from tests.conftest import point_const_to_tmpdir, MockObject


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
def mock_system(monkeypatch):
    monkeypatch.setattr(webcam.main, 'System', MockSystem)



class MockSystem:
    """
        Object that can simulates System.
    """
    @staticmethod
    def report_general_status():
        return {'test-message':'good'}
    @staticmethod
    def apply_system_settings(settings):
        return


def test_main_no_initial_config(mock_system, logs):
    main()
    assert len(logs) > 0
    assert "Failed to load the initial configuration" in logs[-3]['msg'] 
    assert "No configuration file found" in logs[-3]['msg'] 
    assert "Exiting" in logs[-3]['msg'] 
    assert "Execution completed with errors" in logs[-2]['msg']     
    assert "=============" in logs[-1]['msg'] 