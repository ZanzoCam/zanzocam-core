import os
import shutil
import pytest
import logging
from pathlib import Path, PosixPath

import webcam
import constants


class MockObject:
    """
        Object that can be init with a dict.
        Can mock Configuration objects, but servers too
        to some degree
    """
    def __init__(self, values):
        self.send_diagnostics = False
        for key, value in values.items():
            setattr(self, key, value)
    
    def __getattr__(self, *a, **k):
        return lambda *a, **k: None


class MyMock:
    def __init__(self, *a, **k):
        pass
    
    def __getattr__(self, *a, **k):
        return lambda *a, **k: None



def point_const_to_tmpdir(modules, monkeypatch, tmpdir):
    """
        Mocks all the calues in constants.py to point to the 
        pytest temp directory.
    """
    os.mkdir(tmpdir / "data")
    os.mkdir(tmpdir / "web_ui")
    os.mkdir(tmpdir / "data" / "overlays")

    base_path = str(constants.BASE_PATH.absolute()).strip()
    test_path = str(tmpdir).strip()
    for const, value in vars(constants).items():
        if (not const.startswith("_") and
                (isinstance(value, str) or 
                isinstance(value, PosixPath)
            )):
            new_value = str(value).replace(base_path, test_path)

            if isinstance(value, PosixPath):
                new_value = Path(new_value)

            monkeypatch.setattr(constants, const, new_value)
            for module in modules:
                monkeypatch.setattr(module, const, new_value)
            

@pytest.fixture
def logs(monkeypatch):
    logs = []

    def mock_log(msg, *args, **kwargs):
        print(msg)
        logs.append(msg)
    
    logging.info = mock_log
    yield logs
    logs = []


def in_logs(logs, string):
    """
        Looks for a string in the entire logs stack
    """
    total = "\n".join(logs)
    try:
        where = total.index(string) + 1  # So that 0 == not found
        print(f"---------> {string}: {where}")
        return True
    except ValueError:
        return False