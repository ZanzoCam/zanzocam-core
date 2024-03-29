import os
import pytest
from tests.conftest import in_logs

import zanzocam.webcam as webcam
from zanzocam import constants
from zanzocam.webcam.utils import log
from zanzocam.webcam.configuration import Configuration
from zanzocam.webcam.server.server import Server
from zanzocam.webcam.server.ftp_server import FtpServer


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
        log(f"[TEST - SENDING LOGS from {path}]")

    def upload_picture(self, *a, **k):
        pass


@pytest.fixture(autouse=True)
def mock_server_implementations(monkeypatch, tmp_path):
    monkeypatch.setattr(webcam.server.server, 'HttpServer', MockServerImplementation)
    monkeypatch.setattr(webcam.server.server, 'FtpServer', MockServerImplementation)
    monkeypatch.setattr(webcam.server.server, "CONFIGURATION_FILE", tmp_path / "data" / "configuration.json")
    monkeypatch.setattr(webcam.configuration, "CONFIGURATION_FILE", tmp_path / "data" / "configuration.json")


@pytest.fixture(autouse=True)
def mock_sleep(monkeypatch):
    monkeypatch.setattr(webcam.utils, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(webcam.server.server, "sleep", lambda *a, **k: None)


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


def test_update_config_works(tmp_path, logs):
    """
        server.update_config downloads the new config, backs up the old
        configuration and returns the new Configuration object.
    """
    with open(webcam.server.server.CONFIGURATION_FILE, 'w') as c:
        c.write('{"config": "old"}')

    old_config = Configuration()

    server = Server({'protocol': 'http'})
    server.update_configuration(old_config)

    assert not in_logs(logs, "ERROR")

    new_conf_content = open(webcam.server.server.CONFIGURATION_FILE, 'r').read()
    assert "".join(new_conf_content.split()) == '{"config":"new"}'
    
    old_conf_content = open(str(webcam.server.server.CONFIGURATION_FILE) + ".bak", 'r').read()
    assert "".join(old_conf_content.split()) == '{"config":"old"}'


def test_download_overlay_images_works_with_empty_list(logs):
    server = Server({'protocol': 'http'})
    server.download_overlay_images([]) 
    assert not in_logs(logs, "ERROR")


def test_download_overlay_images_works_with_list(logs):
    server = Server({'protocol': 'http'})
    server.download_overlay_images(['test.jpg'])
    assert not in_logs(logs, "ERROR")
    assert in_logs(logs, f"'test.jpg'")


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
    assert in_logs(logs, "ERROR")
    assert in_logs(logs, f"[TEST] Downloading overlay image '1.jpg'")
    assert in_logs(logs, f"New overlay image failed to download: '2.jpg'")
    assert in_logs(logs, f"Ignoring it")
    assert in_logs(logs, f"[TEST] Downloading overlay image '3.jpg'")


def test_upload_logs_works(logs):
    os.makedirs(constants.CAMERA_LOGS)
    with open(webcam.server.server.CAMERA_LOG, 'w') as c:
        c.write('test logs')

    server = Server({'protocol': 'http'})
    server.upload_logs()

    assert in_logs(logs, f"TEST - SENDING LOGS")
    assert not in_logs(logs, "ERROR")
    assert open(webcam.server.server.CAMERA_LOG, 'r').read() == "test logs"


def test_upload_logs_with_path(tmpdir, logs):
    with open(tmpdir / 'random-file', 'w') as c:
        c.write('test logs')

    server = Server({'protocol': 'http'})
    server.upload_logs(path = tmpdir / 'random-file')

    assert not in_logs(logs, "ERROR")
    assert f"[TEST - SENDING LOGS from {tmpdir / 'random-file'}]" in logs[0]
    assert open(tmpdir / 'random-file', 'r').read() == "test logs"  # logs are not deleted


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

    assert not in_logs(logs, "ERROR")
    assert in_logs(logs, "Picture 'test-pic-3.jpg' uploaded successfully")
    assert in_logs(logs, "Pictures deleted successfully")
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

    assert not in_logs(logs, "ERROR")
    assert in_logs(logs, "Picture 'test-pic-3.jpg' uploaded successfully")
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

    assert in_logs(logs, "ERROR")
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
    with pytest.raises(ValueError, match="No picture to upload"):
        server.upload_picture(tmpdir / ".temp.jpg", 'test-pic', 'jpg')

    assert in_logs(logs, "ERROR")
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
    with pytest.raises(ValueError, match="Cannot upload the picture"):
        server.upload_picture(None, 'test-pic', 'jpg')
    assert in_logs(logs, "ERROR")
    assert not os.path.exists(tmpdir / ".temp.jpg")

    with pytest.raises(ValueError, match="Cannot upload the picture") as e:
        server.upload_picture(tmpdir / ".temp.jpg", '', 'jpg')
    assert in_logs(logs, "ERROR")
    assert not os.path.exists(tmpdir / ".temp.jpg")

    with pytest.raises(ValueError, match="Cannot upload the picture") as e:
        server.upload_picture(tmpdir / ".temp.jpg", 'test-pic', '')
    assert in_logs(logs, "ERROR")
    assert not os.path.exists(tmpdir / ".temp.jpg")


def test_create_server_ftp(monkeypatch, logs):

    class MockFTP:
        def __init__(self, *a, **k):
            pass
        def prot_p(self, *a, **k):
            pass

    monkeypatch.setattr(webcam.server.server, 'FtpServer', FtpServer)
    monkeypatch.setattr(webcam.server.ftp_server, "FTP", MockFTP)
    monkeypatch.setattr(webcam.server.ftp_server, "FTP_TLS", MockFTP)
    monkeypatch.setattr(webcam.server.ftp_server, "_Patched_FTP_TLS", MockFTP)

    server = Server({
        'protocol': 'FtP', 
        'hostname': 'me.it', 
        'username': 'me',
    })
    assert server.protocol == "FTP"
    assert isinstance(server._server, FtpServer)
    assert not in_logs(logs, "ERROR")

    server = Server({
        'protocol': 'FtP', 
        'hostname': 'me.it', 
        'username': 'me',
        'tls': False,
    })
    assert server.protocol == "FTP"
    assert isinstance(server._server, FtpServer)
    assert not in_logs(logs, "ERROR")


def test_create_server_http(monkeypatch, logs):

    class MockHttpServer:
        def __init__(self, *a, **k):
            pass

    monkeypatch.setattr(webcam.server.server, 'HttpServer', MockHttpServer)
    
    server = Server({'protocol': 'hTtP', 'url': 'test'})
    assert server.protocol == "HTTP"
    assert isinstance(server._server, MockHttpServer)
    assert not in_logs(logs, "ERROR")
