import os
import pytest
from pathlib import Path
from textwrap import dedent
from freezegun import freeze_time
from PIL import Image, ImageChops
from datetime import datetime, timedelta

import webcam
import constants
from webcam.errors import ServerError
from webcam.server.server import Server
from webcam.server.ftp_server import FtpServer



def test_create_ftpserver_no_dict(logs):
    with pytest.raises(ValueError) as e:
        server = FtpServer("hello")
        assert "FtpServer can only be instantiated with a dictionary" in str(e)
    assert len(logs) == 0


def test_create_ftpserver_host_only(logs):
    with pytest.raises(ServerError) as e:
        server = FtpServer({'hostname': 'me.it'})
        assert "no username found in the configuration" in str(e)
    assert len(logs) == 0


def test_create_ftpserver_username_only(logs):
    with pytest.raises(ServerError) as e:
        server = FtpServer({'username': 'me'})
        assert "no hostname found in the configuration" in str(e)
    assert len(logs) == 0


def test_create_ftpserver_ftplib_fails(monkeypatch, logs):
    monkeypatch.setattr(
        webcam.server.ftp_server.FTP,
        "__init__",
        lambda *a, **k: 1/0
    )
    with pytest.raises(ServerError) as e:
        server = FtpServer({'hostname': 'me.it', 'username': 'me'})
        assert "Failed to estabilish a connection with the FTP server" in str(e)
    assert len(logs) == 0


def test_create_ftpserver_tls_uses_prot_p(monkeypatch, logs):
    monkeypatch.setattr(
        webcam.server.ftp_server.FTP,
        'prot_p',
        lambda s: webcam.utils.log("~~test~~")
    )
    server = FtpServer({'hostname': 'me.it', 
                        'username': 'me', 
                        'tls': True})
    assert len(logs) == 1
    assert "~~test~~" in logs[0]


def test_create_ftpserver_notls_doesnt_use_prot_p(monkeypatch, logs):
    monkeypatch.setattr(
        webcam.server.ftp_server.FTP,
        'prot_p',
        lambda s: webcam.utils.log("~~test~~")
    )
    server = FtpServer({'hostname': 'me.it', 
                        'username': 'test', 
                        'tls': False})
    assert len(logs) == 0


def test_create_ftpserver_subfolder_is_used(monkeypatch, logs):
    monkeypatch.setattr(
        webcam.server.ftp_server.FTP,
        'cwd',
        lambda f, *a, **k: webcam.utils.log("~~cwd~~")
    )
    server = FtpServer({'hostname': 'me.it', 
                        'username': 'me', 
                        'subfolder': 'test'})
    assert len(logs) == 1
    assert "~~cwd~~" in logs[0]


def test_download_new_configuration_succeed(monkeypatch, logs):

    def retrbinary(self, command, callback):
        for line in ['{', '"test": "config"', '}']:
            callback(line.encode(constants.FTP_CONFIG_FILE_ENCODING))
        return "226 OK"

    monkeypatch.setattr(webcam.server.ftp_server.FTP, 'retrbinary', retrbinary)

    server = FtpServer({'hostname': 'me.it', 
                        'username': 'me'})
    config = server.download_new_configuration()
    assert len(logs) == 0
    assert config == {"test": "config"}


def test_download_new_configuration_ftp_error_code(monkeypatch, logs):
    monkeypatch.setattr(
        webcam.server.ftp_server.FTP,
        'retrbinary',
        lambda *a, **k: "550 FAIL"
    )
    server = FtpServer({'hostname': 'me.it', 
                        'username': 'me'})
    with pytest.raises(ServerError) as e:
        server.download_new_configuration()
        assert "The server replied with an error code: 550 FAIL" in str(e)
    assert len(logs) == 0


def test_download_new_configuration_python_error(monkeypatch, logs):
    monkeypatch.setattr(
        webcam.server.ftp_server.FTP,
        'retrbinary',
        lambda *a, **k: 1/0
    )
    server = FtpServer({'hostname': 'me.it', 
                        'username': 'me'})
    with pytest.raises(ZeroDivisionError) as e:
        server.download_new_configuration()
    assert len(logs) == 0
        

def test_download_overlay_image_succeed(monkeypatch, tmpdir, logs):

    def retrbinary(self, command, callback):
        image = Image.new("RGB", (10, 10), color="#FFFFFF")
        image.save(str(tmpdir/'test.png'))
        with open(tmpdir/'test.png', 'rb') as o:
            callback(o.read())
        return "226 OK"

    monkeypatch.setattr(webcam.server.ftp_server.FTP, 'retrbinary', retrbinary)

    server = FtpServer({'hostname': 'me.it', 
                        'username': 'me'})
    server.download_overlay_image('test.png')
    assert len(logs) == 1
    assert "New overlay image downloaded: test.png" in logs[0]
    overlay = Image.open(str(tmpdir/'test.png'))
    downloaded = Image.open(str(constants.IMAGE_OVERLAYS_PATH/'test.png'))
    assert not ImageChops.difference(overlay, downloaded).getbbox()


def test_download_overlay_image_ftp_error_code(monkeypatch, logs):
    monkeypatch.setattr(
        webcam.server.ftp_server.FTP,
        'retrbinary',
        lambda *a, **k: "550 FAIL"
    )
    server = FtpServer({'hostname': 'me.it', 
                        'username': 'me'})
    with pytest.raises(ServerError) as e:
        server.download_overlay_image('test.png')
        assert "The server replied with an error code for 'test.png': 550 FAIL" in str(e)
    assert len(logs) == 0


def test_download_overlay_image_python_error(monkeypatch, logs):
    monkeypatch.setattr(
        webcam.server.ftp_server.FTP,
        'retrbinary',
        lambda *a, **k: 1/0
    )
    server = FtpServer({'hostname': 'me.it', 
                        'username': 'me'})
    with pytest.raises(ZeroDivisionError) as e:
        server.download_overlay_image('test.png')
    assert len(logs) == 0
        

def test_send_logs_no_log_file_to_send(monkeypatch, tmpdir, logs):

    def storlines(self, command, lines):
        with open(tmpdir/"received_logs", 'wb') as r:
            r.writelines(lines)
        return "226 OK"

    monkeypatch.setattr(webcam.server.ftp_server.FTP, 'storlines', storlines)

    server = FtpServer({'hostname': 'me.it', 
                        'username': 'me'})
    server.send_logs(tmpdir/'logs.txt')

    assert len(logs) == 0
    assert open(tmpdir/"received_logs", 'r').read().strip() != ""


def test_send_logs_no_logs_to_send(monkeypatch, tmpdir, logs):

    def storlines(self, command, lines):
        with open(tmpdir/"received_logs", 'wb') as r:
            r.writelines(lines)
        return "226 OK"

    monkeypatch.setattr(webcam.server.ftp_server.FTP, 'storlines', storlines)
    with open(tmpdir/'logs.txt', 'w') as r:
        r.write("    ")

    server = FtpServer({'hostname': 'me.it', 
                        'username': 'me'})
    server.send_logs(tmpdir/'logs.txt')

    assert len(logs) == 0
    assert open(tmpdir/"received_logs", 'r').read().strip() != ""


def test_send_logs_no_logs_to_send_cant_write_mock(monkeypatch, tmpdir, logs):

    def storlines(self, command, lines):
        with open(tmpdir/"received_logs", 'wb') as r:
            r.writelines(lines)
        return "226 OK"

    monkeypatch.setattr(webcam.server.ftp_server.FTP, 'storlines', storlines)
    
    with open(tmpdir/'logs.txt', 'w') as r:
        pass
    os.chmod(tmpdir/'logs.txt', 0o000)

    server = FtpServer({'hostname': 'me.it', 
                        'username': 'me'})

    server.send_logs(tmpdir/'logs.txt')

    assert len(logs) == 1
    assert "No logs were found and no mock log file can be written."\
           "Logs won't be uploaded." in logs[0]
    assert not os.path.exists(tmpdir/"received_logs")


def test_send_logs_some_logs_to_send(monkeypatch, tmpdir, logs):

    def storlines(self, command, lines):
        with open(tmpdir/"received_logs", 'wb') as r:
            r.writelines(lines)
        return "226 OK"

    monkeypatch.setattr(webcam.server.ftp_server.FTP, 'storlines', storlines)
    
    log_content = "some logs\nsome more logs\nùìàòèé'."
    with open(tmpdir/'logs.txt', 'w') as r:
        r.write(log_content)

    server = FtpServer({'hostname': 'me.it', 
                        'username': 'me'})
    server.send_logs(tmpdir/'logs.txt')

    assert len(logs) == 0
    assert open(tmpdir/"received_logs", 'r').read() == log_content


def test_send_logs_ftp_error_code(monkeypatch, tmpdir, logs):

    def storlines(self, command, lines):
        return "550 FAIL"

    monkeypatch.setattr(webcam.server.ftp_server.FTP, 'storlines', storlines)

    server = FtpServer({'hostname': 'me.it', 
                        'username': 'me'})
    with pytest.raises(ServerError) as e:
        server.send_logs(tmpdir/'logs.txt')
        assert "The server replied with an error code while " \
               "uploading the logs: 550 FAIL" in str(e)
    assert len(logs) == 0


def test_send_logs_python_error(monkeypatch, tmpdir, logs):

    monkeypatch.setattr(webcam.server.ftp_server.FTP, 
                        'storlines', 
                        lambda *a, **k: 1/0)

    server = FtpServer({'hostname': 'me.it', 
                        'username': 'me'})
    with pytest.raises(ZeroDivisionError) as e:
        server.send_logs(tmpdir/'logs.txt')
        assert "The server replied with an error code while " \
               "uploading the logs: 550 FAIL" in str(e)
    assert len(logs) == 0


@freeze_time("2021-01-01 12:00:00")
def test_upload_picture_max_0_photo_serverside(monkeypatch, tmpdir, logs):

    def storbinary(self, command, file_handle):
        name = command[14:]
        with open(tmpdir/("r_"+name), 'wb') as r:
            r.write(file_handle.read())
        return "226 OK"

    monkeypatch.setattr(webcam.server.ftp_server.FTP, 'storbinary', storbinary)
    image = Image.new("RGB", (10, 10), color="#FFFFFF")
    image.save(str(tmpdir/'pic.jpg'))

    server = FtpServer({'hostname': 'me.it', 
                        'username': 'me',
                        'max_photos': 0})
    server.upload_picture(tmpdir/'pic.jpg', 'test', 'JPEG')

    assert len(logs) == 0
    sent = Image.open(str(tmpdir/'test_2021-01-01_12:00:00.JPEG'))
    received = Image.open(str(tmpdir/'r_test_2021-01-01_12:00:00.JPEG'))
    assert not ImageChops.difference(sent, received).getbbox()


def test_upload_picture_max_1_photo_serverside(monkeypatch, tmpdir, logs):

    def storbinary(self, command, file_handle):
        name = command[14:]
        with open(tmpdir/("r_"+name), 'wb') as r:
            r.write(file_handle.read())
        return "226 OK"

    monkeypatch.setattr(webcam.server.ftp_server.FTP, 'storbinary', storbinary)
    image = Image.new("RGB", (10, 10), color="#FFFFFF")
    image.save(str(tmpdir/'pic.jpg'))

    server = FtpServer({'hostname': 'me.it', 
                        'username': 'me',
                        'max_photos': 1})
    server.upload_picture(tmpdir/'pic.jpg', 'test', 'JPEG')

    assert len(logs) == 0
    sent = Image.open(str(tmpdir/'test.JPEG'))
    received = Image.open(str(tmpdir/'r_test.JPEG'))
    assert not ImageChops.difference(sent, received).getbbox()


def test_upload_picture_max_3_photo_serverside_server_full(monkeypatch, tmpdir, logs):

    def storbinary(self, command, file_handle):
        name = command[14:]
        with open(tmpdir/('r_'+name), 'wb') as r:
            r.write(file_handle.read())
        return "226 OK"

    def rename(self, old, new):
        webcam.utils.log(f"[TEST] {old} -> {new}")
        return "226 OK"

    monkeypatch.setattr(webcam.server.ftp_server.FTP, 'storbinary', storbinary)
    monkeypatch.setattr(webcam.server.ftp_server.FTP, 'rename', rename)
    image = Image.new("RGB", (10, 10), color="#FFFFFF")
    image.save(str(tmpdir/'pic.jpg'))

    server = FtpServer({'hostname': 'me.it', 
                        'username': 'me',
                        'max_photos': 3})
    server.upload_picture(tmpdir/'pic.jpg', 'test', 'JPEG')

    assert len(logs) == 4
    assert "Renaming pictures of the server..." in logs[0]
    assert "[TEST] pictures/test__2.JPEG -> pictures/test__3.JPEG" in logs[1]
    assert "[TEST] pictures/test__1.JPEG -> pictures/test__2.JPEG" in logs[2]
    assert "[TEST] pictures/test__0.JPEG -> pictures/test__1.JPEG" in logs[3]
    sent = Image.open(str(tmpdir/'test__0.JPEG'))
    received = Image.open(str(tmpdir/'r_test__0.JPEG'))
    assert not ImageChops.difference(sent, received).getbbox()


def test_upload_picture_max_3_photo_serverside_server_empty(monkeypatch, tmpdir, logs):

    def storbinary(self, command, file_handle):
        name = command[14:]
        with open(tmpdir/('r_'+name), 'wb') as r:
            r.write(file_handle.read())
        return "226 OK"

    def rename(self, old, new):
        raise ValueError("550 FAIL")

    monkeypatch.setattr(webcam.server.ftp_server.FTP, 'storbinary', storbinary)
    monkeypatch.setattr(webcam.server.ftp_server.FTP, 'rename', rename)
    image = Image.new("RGB", (10, 10), color="#FFFFFF")
    image.save(str(tmpdir/'pic.jpg'))

    server = FtpServer({'hostname': 'me.it', 
                        'username': 'me',
                        'max_photos': 3})
    server.upload_picture(tmpdir/'pic.jpg', 'test', 'JPEG')

    assert len(logs) == 4
    assert "Renaming pictures of the server..." in logs[0]
    assert "Probably the image didn't exist. Ignoring" in logs[1]
    assert "Probably the image didn't exist. Ignoring" in logs[2]
    assert "Probably the image didn't exist. Ignoring" in logs[3]
    sent = Image.open(str(tmpdir/'test__0.JPEG'))
    received = Image.open(str(tmpdir/'r_test__0.JPEG'))
    assert not ImageChops.difference(sent, received).getbbox()


def test_upload_picture_missing_picture(monkeypatch, tmpdir, logs):

    def storbinary(self, command, file_handle):
        name = command[14:]
        with open(tmpdir/("r_"+name), 'wb') as r:
            r.write(file_handle.read())
        return "226 OK"

    monkeypatch.setattr(webcam.server.ftp_server.FTP, 'storbinary', storbinary)
    
    server = FtpServer({'hostname': 'me.it', 
                        'username': 'me',
                        'max_photos': 1})
    with pytest.raises(ServerError) as e:
        server.upload_picture(tmpdir/'pic.jpg', 'test', 'JPEG')
        assert "No picture to upload" in str(e)

    assert len(logs) == 0
    assert not os.path.exists(tmpdir/'test.JPEG')
    assert not os.path.exists(tmpdir/'r_test.JPEG')


def test_upload_picture_ftp_error_code(monkeypatch, tmpdir, logs):

    def storbinary(self, command, file_handle):
        return "550 FAIL"

    monkeypatch.setattr(webcam.server.ftp_server.FTP, 'storbinary', storbinary)
    image = Image.new("RGB", (10, 10), color="#FFFFFF")
    image.save(str(tmpdir/'pic.jpg'))

    server = FtpServer({'hostname': 'me.it', 
                        'username': 'me',
                        'max_photos': 1})
    with pytest.raises(ServerError) as e:
        server.upload_picture(tmpdir/'pic.jpg', 'test', 'JPEG')
        assert "The server replied with an error code" in str(e)
        assert "The image was probably not sent" in str(e)
        assert "550 FAIL" in str(e)

    assert len(logs) == 0
    assert os.path.exists(tmpdir/'test.JPEG')
    assert not os.path.exists(tmpdir/'r_test.JPEG')


def test_upload_picture_python_error(monkeypatch, tmpdir, logs):

    monkeypatch.setattr(webcam.server.ftp_server.FTP, 
                        'storbinary', 
                        lambda *a, **k: 1/0)
    
    server = FtpServer({'hostname': 'me.it', 
                        'username': 'me',
                        'max_photos': 1})

    image = Image.new("RGB", (10, 10), color="#FFFFFF")
    image.save(str(tmpdir/'pic.jpg'))

    with pytest.raises(ZeroDivisionError) as e:
        server.upload_picture(tmpdir/'pic.jpg', 'test', 'JPEG')

    assert len(logs) == 0
    assert os.path.exists(tmpdir/'test.JPEG')
    assert not os.path.exists(tmpdir/'r_test.JPEG')
