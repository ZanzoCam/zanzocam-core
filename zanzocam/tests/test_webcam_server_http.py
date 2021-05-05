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



def test_create_server_http(monkeypatch, logs):
    """
        The HTTP version can be instantiated without issues
    """
    class MockHttpServer(MockObject):
        pass

    monkeypatch.setattr(webcam.server.server, 'HttpServer', MockHttpServer)
    
    server = Server({'protocol': 'hTtP'})
    assert server.protocol == "HTTP"
    assert isinstance(server._server, MockHttpServer)
    assert len(logs) == 0
