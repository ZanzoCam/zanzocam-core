import os
import pytest
from pathlib import Path
from textwrap import dedent
from unittest.mock import Mock
from freezegun import freeze_time
from datetime import datetime, timedelta

import webcam
import constants
from webcam.utils import log
from webcam.configuration import Configuration
from webcam.server.server import Server

from tests.conftest import point_const_to_tmpdir, MockObject


class MockServerImplementation:
    def __init__(self, values):
        for key, value in values.items():
            setattr(self, key, value)
    
    def __getattr__(self, *a, **k):
        return lambda *a, **k: None
        
    def download_new_configuration(self):
        return {'config': 'new'}

    def download_overlay_image(self, image):
        log(f"[TEST] Downloading overlay image '{image}' - mocked")

    def send_logs(self, path):
        log(f"[TEST - SENDING LOGS from {path}]\n{open(path, 'r').read()}")

    def upload_picture(self, *a, **k):
        pass


@pytest.fixture(autouse=True)
def point_to_tmpdir(monkeypatch, tmpdir):
    point_const_to_tmpdir([webcam.server.server, webcam.configuration], 
        monkeypatch, tmpdir)


@pytest.fixture(autouse=True)
def mock_server_implementations(monkeypatch):
    monkeypatch.setattr(webcam.server.server, 'HttpServer', MockServerImplementation)
    monkeypatch.setattr(webcam.server.server, 'FtpServer', MockServerImplementation)



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


def test_update_config_works(logs):
    """
        server.update_config downloads the new config, backs up the old
        configuration and returns the new Configuration object.
    """
    with open(webcam.server.server.CONFIGURATION_FILE, 'w') as c:
        c.write('{"config": "old"}')

    old_config = Configuration()

    server = Server({'protocol': 'http'})
    new_config = server.update_configuration(old_config)

    assert len(logs) == 0
    
    new_conf_content = open(webcam.server.server.CONFIGURATION_FILE, 'r').read()
    assert "".join(new_conf_content.split()) == '{"config":"new"}'
    
    old_conf_content = open(str(webcam.server.server.CONFIGURATION_FILE) + ".bak", 'r').read()
    assert "".join(old_conf_content.split()) == '{"config":"old"}'


def test_download_overlay_images_works_with_empty_list(logs):
    server = Server({'protocol': 'http'})
    server.download_overlay_images([])
    assert len(logs) == 0


def test_download_overlay_images_works_with_list(logs):
    server = Server({'protocol': 'http'})
    server.download_overlay_images(['test.jpg'])
    assert len(logs) == 1
    assert f"[TEST] Downloading overlay image 'test.jpg'" in logs[0]


def test_download_overlay_images_fail(monkeypatch, logs):
    def download_mocked(self, image):
        if image == "2.jpg":
            raise Exception("Test exception")
        log(f"[TEST] Downloading overlay image '{image}'"),
        
    monkeypatch.setattr(
        webcam.server.server.HttpServer, 
        'download_overlay_image',
        download_mocked
    )
    server = Server({'protocol': 'http'})
    server.download_overlay_images(['1.jpg', '2.jpg', '3.jpg'])
    assert len(logs) == 3
    assert f"[TEST] Downloading overlay image '1.jpg'" in logs[0]
    assert f"New overlay image failed to download: '2.jpg'" in logs[1]
    assert f"[TEST] Downloading overlay image '3.jpg'" in logs[2]


def test_upload_logs_works(logs):
    with open(webcam.server.server.CAMERA_LOG, 'w') as c:
        c.write('test logs')

    server = Server({'protocol': 'http'})
    server.upload_logs()

    assert len(logs) == 1
    assert f"[TEST - SENDING LOGS from {webcam.server.server.CAMERA_LOG}]" in logs[0]
    assert open(webcam.server.server.CAMERA_LOG, 'r').read() == ""


def test_upload_logs_with_path(tmpdir, logs):
    with open(tmpdir / 'random-file', 'w') as c:
        c.write('test logs')

    server = Server({'protocol': 'http'})
    server.upload_logs(path = tmpdir / 'random-file')

    assert len(logs) == 1
    assert f"[TEST - SENDING LOGS from {tmpdir / 'random-file'}]" in logs[0]
    assert open(tmpdir / 'random-file', 'r').read() == ""


def test_upload_logs_fails(monkeypatch, logs):
    with open(webcam.server.server.CAMERA_LOG, 'w') as c:
        c.write('test logs')

    monkeypatch.setattr(
        webcam.server.server.HttpServer, 
        'send_logs',
        lambda *a, **k: 1/0
    )

    server = Server({'protocol': 'http'})
    with pytest.raises(ZeroDivisionError):
        server.upload_logs()

    assert len(logs) == 0
    assert open(webcam.server.server.CAMERA_LOG, 'r').read() == "test logs"


def test_upload_failure_report_works(monkeypatch, logs):
    with open(webcam.server.server.CAMERA_LOG, 'w') as c:
        c.write('test logs')
    
    server = Server({'protocol': 'http'})
    server.upload_failure_report({'conf': 'wrong'}, {'conf': 'right'})
    
    assert len(logs) == 1
    assert f"[TEST - SENDING LOGS from {webcam.server.server.FAILURE_REPORT_PATH}]" in logs[0]
    assert open(webcam.server.server.CAMERA_LOG, 'r').read() == "test logs"
    assert open(webcam.server.server.FAILURE_REPORT_PATH, 'r').read() == ""


def test_upload_failure_report_finds_no_logs(monkeypatch, logs):
    server = Server({'protocol': 'http'})
    server.upload_failure_report({'conf': 'wrong'}, {'conf': 'right'})
    
    assert len(logs) == 1
    assert f"[TEST - SENDING LOGS from {webcam.server.server.FAILURE_REPORT_PATH}]" in logs[0]
    assert "==> No logs found <==" in logs[0]
    assert open(webcam.server.server.FAILURE_REPORT_PATH, 'r').read() == ""


def test_upload_failure_report_cant_read_logs(monkeypatch, logs):
    with open(webcam.server.server.CAMERA_LOG, 'w') as c:
        c.write('test logs')
    os.chmod(webcam.server.server.CAMERA_LOG, 0o222)
    
    server = Server({'protocol': 'http'})
    server.upload_failure_report({'conf': 'wrong'}, {'conf': 'right'})
    
    assert len(logs) == 2
    assert f"[TEST - SENDING LOGS from {webcam.server.server.FAILURE_REPORT_PATH}]" in logs[1]
    assert "An error occurred opening the logs file and the logs " \
           "could not be read" in logs[1]
    os.chmod(webcam.server.server.CAMERA_LOG, 0o777)
    assert open(webcam.server.server.CAMERA_LOG, 'r').read() == "test logs"
    assert open(webcam.server.server.FAILURE_REPORT_PATH, 'r').read() == ""




def test_upload_picture_works(monkeypatch, tmpdir, logs):
    with open(tmpdir / ".temp.jpg", 'w') as c:
        pass

    def upload_picture(self, image_path, image_name, image_extension):
        with open(tmpdir / 'test-pic-3.jpg', 'w') as c:
            pass
        return tmpdir / "test-pic-3.jpg"

    monkeypatch.setattr(
        webcam.server.server.HttpServer, 
        'upload_picture',
        upload_picture
    )

    server = Server({'protocol': 'http'})
    server.upload_picture(tmpdir / ".temp.jpg", 'test-pic', 'jpg')

    assert len(logs) == 2
    assert "Picture 'test-pic-3.jpg' uploaded successfully" in logs[0]
    assert "Pictures deleted successfully" in logs[1]
    assert not os.path.exists(tmpdir / ".temp.jpg")


def test_upload_picture_no_cleanup(monkeypatch, tmpdir, logs):
    with open(tmpdir / ".temp.jpg", 'w') as c:
        pass
    
    def upload_picture(self, image_path, image_name, image_extension):
        with open(tmpdir / 'test-pic-3.jpg', 'w') as c:
            pass
        return tmpdir / "test-pic-3.jpg"

    monkeypatch.setattr(
        webcam.server.server.HttpServer, 
        'upload_picture',
        upload_picture
    )

    server = Server({'protocol': 'http'})
    server.upload_picture(tmpdir / ".temp.jpg", 'test-pic', 'jpg', cleanup = False)

    assert len(logs) == 1
    assert "Picture 'test-pic-3.jpg' uploaded successfully" in logs[0]
    assert os.path.exists(tmpdir / ".temp.jpg")


def test_upload_picture_does_not_catch_exceptions(monkeypatch, tmpdir, logs):
    with open(tmpdir / ".temp.jpg", 'w') as c:
        pass
    
    monkeypatch.setattr(
        webcam.server.server.HttpServer, 
        'upload_picture',
        lambda *a, **k: 1/0
    )

    server = Server({'protocol': 'http'})
    with pytest.raises(ZeroDivisionError):
        server.upload_picture(tmpdir / ".temp.jpg", 'test-pic', 'jpg')

    assert len(logs) == 0
    assert os.path.exists(tmpdir / ".temp.jpg")


def test_upload_picture_needs_correct_path(monkeypatch, tmpdir, logs):
    
    def upload_picture(self, image_path, image_name, image_extension):
        with open(tmpdir / 'test-pic-3.jpg', 'w') as c:
            pass
        return tmpdir / "test-pic-3.jpg"

    monkeypatch.setattr(
        webcam.server.server.HttpServer, 
        'upload_picture',
        upload_picture
    )

    server = Server({'protocol': 'http'})
    with pytest.raises(ValueError) as e:
        server.upload_picture(tmpdir / ".temp.jpg", 'test-pic', 'jpg')
        assert "No picture to upload" in str(e)

    assert len(logs) == 0
    assert not os.path.exists(tmpdir / ".temp.jpg")


def test_upload_picture_needs_path_name_extension(monkeypatch, tmpdir, logs):
    
    def upload_picture(self, image_path, image_name, image_extension):
        with open(tmpdir / 'test-pic-3.jpg', 'w') as c:
            pass
        return tmpdir / "test-pic-3.jpg"

    monkeypatch.setattr(
        webcam.server.server.HttpServer, 
        'upload_picture',
        upload_picture
    )

    server = Server({'protocol': 'http'})
    with pytest.raises(ValueError) as e:
        server.upload_picture(None, 'test-pic', 'jpg')
        assert "Cannot upload the picture" in str(e)

    with pytest.raises(ValueError) as e:
        server.upload_picture(tmpdir / ".temp.jpg", '', 'jpg')
        assert "Cannot upload the picture" in str(e)

    with pytest.raises(ValueError) as e:
        server.upload_picture(tmpdir / ".temp.jpg", 'test-pic', '')
        assert "Cannot upload the picture" in str(e)

    assert len(logs) == 0
    assert not os.path.exists(tmpdir / ".temp.jpg")
