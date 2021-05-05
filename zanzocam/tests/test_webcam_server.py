import os
import pytest
from pathlib import Path
from textwrap import dedent
from freezegun import freeze_time
from datetime import datetime, timedelta

import webcam
import constants
from webcam.configuration import Configuration
from webcam.server.server import Server

from tests.conftest import point_const_to_tmpdir, MockObject


@pytest.fixture(autouse=True)
def point_to_tmpdir(monkeypatch, tmpdir):
    point_const_to_tmpdir([webcam.server.server], monkeypatch, tmpdir)


def test_create_server_no_config(logs):
    """
        A meaningful error is given if no configuration is given
    """
    with pytest.raises(webcam.errors.ServerError) as e:
        Server(None)
        assert "No server information found in the configuration file" \
            in str(e)
    assert len(logs) == 0


def test_create_server_empty_server_block(logs):
    """
        A meaningful error is given if no server data is given
    """
    with pytest.raises(webcam.errors.ServerError) as e:
        Server({})
        assert "No server information found in the configuration file" \
            in str(e)
    assert len(logs) == 0


def test_create_server_wrong_server_block(logs):
    """
        A meaningful error is given if the server data is not a dict
    """
    with pytest.raises(webcam.errors.ServerError) as e:
        Server('wrong!')
        assert "The communication protocol with the server (HTTP, FTP) " \
                "was not specified" in str(e)
    assert len(logs) == 0


def test_create_server_server_block_contains_no_protocol(logs):
    """
        A meaningful error is given if the protocol is not specified
    """
    with pytest.raises(webcam.errors.ServerError) as e:
        Server({'something': 'else'})
        assert "The communication protocol with the server (HTTP, FTP) " \
                "was not specified" in str(e)
    assert len(logs) == 0


def test_create_server_wrong_protocol(logs):
    """
        A meaningful error is given if the protocol has typos
    """
    with pytest.raises(webcam.errors.ServerError) as e:
        Server({'protocol': 'htp'})
        assert "The communication protocol with the server (HTTP, FTP) " \
                "was not specified" in str(e)
    assert len(logs) == 0


def test_create_server_wrong_protocol_2(logs):
    """
        A meaningful error is given if the protocol is not a string
    """
    with pytest.raises(webcam.errors.ServerError) as e:
        Server({'protocol': 1})
        assert "The communication protocol with the server (HTTP, FTP) " \
                "was not specified" in str(e)
    assert len(logs) == 0


def test_get_endpoint_update_config_works(monkeypatch, logs):
    """
        server.update_config downloads the new config, backs up the old
        configuration and returns the new Configuration object.
    """
    class MockHttpServer(MockObject):
        def download_new_configuration(self):
            return {'config': 'new'}

    monkeypatch.setattr(webcam.server.server, 'HttpServer', MockHttpServer)

    with open(webcam.server.server.CONFIGURATION_FILE, 'w') as c:
        c.write('{"config": "old"}')
    old_config = Configuration(
        path = Path(webcam.server.server.CONFIGURATION_FILE))

    server = Server({'protocol': 'http'})
    new_config = server.update_configuration(old_config,
        new_conf_path = Path(webcam.server.server.CONFIGURATION_FILE))

    assert len(logs) == 0
    
    new_conf_content = open(webcam.server.server.CONFIGURATION_FILE, 'r').read()
    assert "".join(new_conf_content.split()) == '{"config":"new"}'
    
    old_conf_content = open(str(webcam.server.server.CONFIGURATION_FILE) + ".bak", 'r').read()
    assert "".join(old_conf_content.split()) == '{"config":"old"}'
