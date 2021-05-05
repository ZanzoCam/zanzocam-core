import os
import pytest
from pathlib import Path
from textwrap import dedent
from freezegun import freeze_time
from datetime import datetime, timedelta

import webcam
import constants
from webcam.server.server import Server

from tests.conftest import point_const_to_tmpdir, MockObject


@pytest.fixture(autouse=True)
def point_to_tmpdir(monkeypatch, tmpdir):
    point_const_to_tmpdir([webcam.server.http_server], monkeypatch, tmpdir)



def test_create_server_ftp(monkeypatch, logs):
    """
        The FTP version can be instantiated without issues
    """
    class MockFtpServer(MockObject):
        pass

    monkeypatch.setattr(webcam.server.server, 'FtpServer', MockFtpServer)
    
    server = Server({'protocol': 'FtP'})
    assert server.protocol == "FTP"
    assert isinstance(server._server, MockFtpServer)
    assert len(logs) == 0
