import os
import shutil
import pytest
import logging
from pathlib import PosixPath

import webcam
import constants


def point_const_to_tmpdir(module, monkeypatch, tmpdir):
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
            value = str(value)
            new_value = value.replace(base_path, test_path)
            monkeypatch.setattr(constants, const, new_value)
            monkeypatch.setattr(module, const, new_value)
            

@pytest.fixture
def logs(monkeypatch):
    logs = []

    def mock_log(msg, *args, **kwargs):
        print(msg)
        logs.append({"msg": msg})
    
    logging.info = mock_log
    yield logs
    logs = []
