import os
import pytest
from pathlib import Path
from textwrap import dedent
from freezegun import freeze_time
from datetime import datetime, timedelta

import webcam
import constants
from webcam.errors import ServerError
from webcam.server.server import Server
from webcam.server.http_server import HttpServer


from tests.conftest import point_const_to_tmpdir


@pytest.fixture(autouse=True)
def point_to_tmpdir(monkeypatch, tmpdir):
    point_const_to_tmpdir([webcam.server.http_server], monkeypatch, tmpdir)


class MockCredentials:
    def __init__(self, u, p):
        pass


@pytest.fixture(autouse=True)
def mock_requests(monkeypatch):
    monkeypatch.setattr(webcam.server.http_server.requests.auth,
                        'HTTPBasicAuth',
                        lambda u, p: MockCredentials(u, p))


def test_create_httpserver_no_dict(logs):
    with pytest.raises(ValueError) as e:
        server = HttpServer("hello")
        assert "HttpServer can only be instantiated with a dictionary" in str(e)
    assert len(logs) == 0


def test_create_httpserver_no_url(logs):
    with pytest.raises(ServerError) as e:
        server = HttpServer({})
        assert "no server URL found" in str(e)
    assert len(logs) == 0


def test_create_httpserver_url_only(logs):
    server = HttpServer({'url': 'test'})
    assert len(logs) == 0
    assert 'credentials' not in vars(server).keys()


def test_create_httpserver_url_and_credentials(logs):
    server = HttpServer({'url': 'test', 'username': 'me', 'password': 'pwd'})
    assert len(logs) == 0
    assert 'credentials' in vars(server).keys()
    assert isinstance(server.credentials, MockCredentials)