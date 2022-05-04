import os
import pytest
from freezegun import freeze_time
from PIL import Image, ImageChops

import zanzocam.webcam as webcam
import zanzocam.constants as constants
from zanzocam.webcam.errors import ServerError
from zanzocam.webcam.server.http_server import HttpServer

from tests.conftest import MockGetRequest, MockPostRequest


@pytest.fixture(autouse=True)
def mock_sleep(monkeypatch):
    monkeypatch.setattr(webcam.utils, "sleep", lambda *a, **k: None)


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
    assert 'credentials' in vars(server).keys()
    assert not server.credentials


def test_create_httpserver_url_and_credentials(logs):
    server = HttpServer({'url': 'test', 'username': 'me', 'password': 'pwd'})
    assert len(logs) == 0
    assert 'credentials' in vars(server).keys()
    assert server.credentials is not None


def test_download_new_configuration_succeed(monkeypatch, logs):
    monkeypatch.setattr(
        webcam.server.http_server.requests,
        'get',
        lambda *a, **k: MockGetRequest('{"configuration": {"test": "data"}}'))

    server = HttpServer({'url': 'test'})
    config = server.download_new_configuration()

    assert len(logs) == 0
    assert config == {"test": "data"}


def test_download_new_configuration_request_fails(monkeypatch, logs):
    monkeypatch.setattr(
        webcam.server.http_server.requests,
        'get',
        lambda *a, **k: 1/0)

    server = HttpServer({'url': 'test'})

    with pytest.raises(ServerError, match="Something went wrong downloading the new configuration"):
        server.download_new_configuration()


def test_download_new_configuration_json_fails(monkeypatch, logs):
    monkeypatch.setattr(
        webcam.server.http_server.requests,
        'get',
        lambda *a, **k: MockGetRequest('{"configuration: {"test": "data"}}'))

    server = HttpServer({'url': 'test'})

    with pytest.raises(ServerError) as e:
        server.download_new_configuration()
        assert "The server did not reply valid JSON" in str(e)
        assert "Full server response" in str(e)
        assert '{"configuration: {"test": "data"}}' in str(e)


def test_download_new_configuration_no_config_key(monkeypatch, logs):
    monkeypatch.setattr(
        webcam.server.http_server.requests,
        'get',
        lambda *a, **k: MockGetRequest('{"conf": {"test": "data"}}'))

    server = HttpServer({'url': 'test'})

    with pytest.raises(ServerError) as e:
        server.download_new_configuration()
        assert "The server did not reply with a configuration file" in str(e)
        assert "Full server response" in str(e)
        assert '{"conf": {"test": "data"}}' in str(e)
    assert len(logs) == 0


def test_download_overlay_image_succeed(monkeypatch, tmpdir, logs):
    image = Image.new("RGBA", (10, 10), color="#FFFFFF99")
    image.save(str(tmpdir/'original_test.png'))

    monkeypatch.setattr(
        webcam.server.http_server.requests,
        'get',
        lambda url, *a, **k: MockGetRequest(
            file_stream=open(tmpdir/'original_test.png', 'rb'))
    )
    server = HttpServer({'url': 'test'})

    server.download_overlay_image('test.png')
    assert len(logs) == 1
    assert "New overlay image downloaded: test.png" in logs[0]
    overlay = Image.open(str(tmpdir/'original_test.png'))
    downloaded = Image.open(str(constants.IMAGE_OVERLAYS_PATH/'test.png'))
    assert not ImageChops.difference(overlay, downloaded).getbbox()


def test_download_overlay_image_request_fail(monkeypatch, tmpdir, logs):
    image = Image.new("RGBA", (10, 10), color="#FFFFFF99")
    image.save(str(tmpdir/'test.png'))

    monkeypatch.setattr(
        webcam.server.http_server.requests,
        'get',
        lambda url, *a, **k: 1/0
    )
    server = HttpServer({'url': 'test'})

    with pytest.raises(ServerError) as e:
        server.download_overlay_image('test.jpg')
        assert "Something went wrong downloading the overlay image 'test.jpg'" in str(e)
        assert "Full server response" in str(e)


def test_download_overlay_image_request_404(monkeypatch, tmpdir, logs):
    image = Image.new("RGBA", (10, 10), color="#FFFFFF99")
    image.save(str(tmpdir/'test.png'))

    monkeypatch.setattr(
        webcam.server.http_server.requests,
        'get',
        lambda url, *a, **k: MockGetRequest(status=404)
    )
    server = HttpServer({'url': 'test'})

    with pytest.raises(ServerError) as e:
        server.download_overlay_image('test.jpg')
        assert "Something went wrong downloading the overlay image 'test.jpg'" in str(e)
        assert "The server replied with status code 404 (TEST REASON)" in str(e)
        assert "Full server response" in str(e)


def test_download_overlay_image_stream_fail(monkeypatch, tmpdir, logs):
    image = Image.new("RGBA", (10, 10), color="#FFFFFF99")
    image.save(str(tmpdir/'test.png'))

    monkeypatch.setattr(
        webcam.server.http_server.requests,
        'get',
        lambda url, *a, **k: MockGetRequest()
    )
    server = HttpServer({'url': 'test'})

    with pytest.raises(ServerError, match="Something went wrong downloading the overlay image 'test.jpg'"):
        server.download_overlay_image('test.jpg')


def test_send_logs_succeed(monkeypatch, tmpdir, logs):
    monkeypatch.setattr(
        webcam.server.http_server.requests,
        'post',
        lambda url, data, *a, **k: MockPostRequest(data=data)
    )

    log_content = "some logs\nsome more logs\nùìàòèé'."
    with open(tmpdir/'logs.txt', 'w') as l:
        l.write(log_content)

    server = HttpServer({'url': 'test'})
    server.send_logs(str(tmpdir/'logs.txt'))

    assert len(logs) == 1
    assert "[TEST] POSTing: " in logs[0]     
    assert f"{ {'logs': log_content} }" in logs[0] 


def test_send_logs_post_fails(monkeypatch, tmpdir, logs):
    monkeypatch.setattr(
        webcam.server.http_server.requests,
        'post',
        lambda url, data, *a, **k: 1/0
    )
    log_content = "some logs\nsome more logs\nùìàòèé'."
    with open(tmpdir/'logs.txt', 'w') as l:
        l.write(log_content)

    server = HttpServer({'url': 'test'})
    with pytest.raises(ServerError) as e:
        server.send_logs(str(tmpdir/'logs.txt'))
        assert "Something went wrong uploading the logs" in str(e)
    assert len(logs) == 0


def test_send_logs_no_logs(monkeypatch, tmpdir, logs):
    monkeypatch.setattr(
        webcam.server.http_server.requests,
        'post',
        lambda url, data, *a, **k: MockPostRequest(data=data)
    )

    server = HttpServer({'url': 'test'})
    server.send_logs(str(tmpdir/'logs.txt'))

    assert len(logs) == 1
    assert "[TEST] POSTing: " in logs[0]     
    assert "{'logs': ' ==> No logs found!! <== '}" in logs[0] 


def test_send_logs_cant_read_logs(monkeypatch, tmpdir, logs):
    monkeypatch.setattr(
        webcam.server.http_server.requests,
        'post',
        lambda url, data, *a, **k: MockPostRequest(data=data)
    )
    with open(tmpdir/'logs.txt', 'w') as l:
        pass
    os.chmod(tmpdir/'logs.txt', 0o000)

    server = HttpServer({'url': 'test'})
    server.send_logs(str(tmpdir/'logs.txt'))

    assert len(logs) == 2
    assert "Something went wrong opening the logs file. " \
           "Sending a mock logfile" in logs[0]
    assert "[TEST] POSTing: " in logs[1]
    assert "Failed to read the log file." in logs[1]


def test_send_logs_response_404(monkeypatch, tmpdir, logs):
    monkeypatch.setattr(
        webcam.server.http_server.requests,
        'post',
        lambda url, data, *a, **k: MockPostRequest(status=404)
    )
    with open(tmpdir/'logs.txt', 'w') as l:
        pass

    server = HttpServer({'url': 'test'})
    with pytest.raises(ServerError) as e:
        server.send_logs(str(tmpdir/'logs.txt'))
        assert "The server replied with status code 404 (TEST REASON)" in str(e)

    assert len(logs) == 0


def test_send_logs_response_json_fails(monkeypatch, tmpdir, logs):
    monkeypatch.setattr(
        webcam.server.http_server.requests,
        'post',
        lambda url, data, *a, **k: MockPostRequest(response="test not json")
    )
    with open(tmpdir/'logs.txt', 'w') as l:
        pass

    server = HttpServer({'url': 'test'})
    with pytest.raises(ServerError) as e:
        server.send_logs(str(tmpdir/'logs.txt'))
        assert "The server did not reply valid JSON." in str(e)

    assert len(logs) == 0


def test_send_logs_response_malformed_response(monkeypatch, tmpdir, logs):
    monkeypatch.setattr(
        webcam.server.http_server.requests,
        'post',
        lambda url, data, *a, **k: MockPostRequest(response="{}")
    )
    with open(tmpdir/'logs.txt', 'w') as l:
        pass

    server = HttpServer({'url': 'test'})
    with pytest.raises(ServerError) as e:
        server.send_logs(str(tmpdir/'logs.txt'))
        assert "The server reply was unexpected." in str(e)

    assert len(logs) == 0


def test_send_logs_response_response_contains_remote_exception(monkeypatch, tmpdir, logs):
    monkeypatch.setattr(
        webcam.server.http_server.requests,
        'post',
        lambda url, data, *a, **k: MockPostRequest(response="{'logs': 'test error!'}")
    )
    with open(tmpdir/'logs.txt', 'w') as l:
        pass

    server = HttpServer({'url': 'test'})
    with pytest.raises(ServerError) as e:
        server.send_logs(str(tmpdir/'logs.txt'))
        assert "The server reply was unexpected." in str(e)
        assert "test error!" in str(e)

    assert len(logs) == 0


@freeze_time("2021-01-01 12:00:00")
def test_upload_picture_max_0_serverside_succeed(monkeypatch, tmpdir, logs):
    image = Image.new("RGB", (100, 100), color="#FFFFFF")
    image.save(str(tmpdir/'test.jpg'))

    monkeypatch.setattr(
        webcam.server.http_server.requests,
        'post',
        lambda url, files, *a, **k: MockPostRequest(image=files, tmpdir=tmpdir)
    )
    # 0 max photos is the default, let's try it out
    server = HttpServer({'url': 'test'})
    server.upload_picture(str(tmpdir/'test.jpg'), 'IMAGE', "JPEG")

    assert len(logs) == 1
    assert "[TEST] POSTing an image" in logs[0]
    sent = Image.open(str(tmpdir/'IMAGE_2021-01-01_12:00:00.JPEG'))
    received = Image.open(str(tmpdir/'received_image.jpg'))
    assert not ImageChops.difference(sent, received).getbbox()


def test_upload_picture_max_1_serverside_succeed(monkeypatch, tmpdir, logs):
    image = Image.new("RGB", (100, 100), color="#FFFFFF")
    image.save(str(tmpdir/'test.jpg'))

    monkeypatch.setattr(
        webcam.server.http_server.requests,
        'post',
        lambda url, files, *a, **k: MockPostRequest(image=files, tmpdir=tmpdir)
    )
    server = HttpServer({'url': 'test', 'max_photos': 1})
    server.upload_picture(str(tmpdir/'test.jpg'), 'IMAGE', "JPEG")

    assert len(logs) == 1
    assert "[TEST] POSTing an image" in logs[0]
    sent = Image.open(str(tmpdir/'IMAGE.JPEG'))
    received = Image.open(str(tmpdir/'received_image.jpg'))
    assert not ImageChops.difference(sent, received).getbbox()


def test_upload_picture_max_3_serverside_succeed(monkeypatch, tmpdir, logs):
    image = Image.new("RGB", (100, 100), color="#FFFFFF")
    image.save(str(tmpdir/'test.jpg'))

    monkeypatch.setattr(
        webcam.server.http_server.requests,
        'post',
        lambda url, files, *a, **k: MockPostRequest(image=files, tmpdir=tmpdir)
    )
    server = HttpServer({'url': 'test', 'max_photos': 3})
    server.upload_picture(str(tmpdir/'test.jpg'), 'IMAGE', "JPEG")

    assert len(logs) == 1
    assert "[TEST] POSTing an image" in logs[0]
    sent = Image.open(str(tmpdir/'IMAGE.JPEG'))
    received = Image.open(str(tmpdir/'received_image.jpg'))
    assert not ImageChops.difference(sent, received).getbbox()


@freeze_time("2021-01-01 12:00:00")
def test_upload_picture_initial_rename_fails(monkeypatch, tmpdir, logs):
    image = Image.new("RGB", (100, 100), color="#FFFFFF")
    image.save(str(tmpdir/'test.jpg'))

    monkeypatch.setattr(
        webcam.server.http_server.requests,
        'post',
        lambda url, files, *a, **k: MockPostRequest(image=files, tmpdir=tmpdir)
    )
    monkeypatch.setattr(
        webcam.server.http_server.os,
        'rename',
        lambda *a, **k: 1/0
    )
    server = HttpServer({'url': 'test'})
    server.upload_picture(str(tmpdir/'test.jpg'), 'IMAGE', "JPEG")

    assert len(logs) == 2
    assert "Something went wrong renaming the image. " \
           "It's going to be sent under its temporary name" in logs[0]
    assert "[TEST] POSTing an image" in logs[1]
    sent = Image.open(str(tmpdir/'test.jpg'))
    received = Image.open(str(tmpdir/'received_image.jpg'))
    assert not ImageChops.difference(sent, received).getbbox()


def test_upload_picture_cant_open_file(monkeypatch, tmpdir, logs):
    image = Image.new("RGB", (100, 100), color="#FFFFFF")
    image.save(str(tmpdir/'test.jpg'))
    os.chmod(tmpdir/'test.jpg', 0o000)

    monkeypatch.setattr(
        webcam.server.http_server.requests,
        'post',
        lambda url, files, *a, **k: MockPostRequest(image=files, tmpdir=tmpdir)
    )
    
    server = HttpServer({'url': 'test', 'max_photos': 1})

    with pytest.raises(ServerError) as e:
        server.upload_picture(str(tmpdir/'test.jpg'), 'IMAGE', "JPEG")
        assert "Something went wrong uploading the picture. " in str(e)
    assert len(logs) == 0


def test_upload_picture_no_file(monkeypatch, tmpdir, logs):
    monkeypatch.setattr(
        webcam.server.http_server.requests,
        'post',
        lambda url, files, *a, **k: MockPostRequest(image=files, tmpdir=tmpdir)
    )
    server = HttpServer({'url': 'test', 'max_photos': 1})
    with pytest.raises(ServerError) as e:
        server.upload_picture(str(tmpdir/'test.jpg'), 'IMAGE', "JPEG")
        assert "No picture to upload" in str(e)

    assert len(logs) == 0


def test_upload_picture_response_404(monkeypatch, tmpdir, logs):
    image = Image.new("RGB", (100, 100), color="#FFFFFF")
    image.save(str(tmpdir/'test.jpg'))

    monkeypatch.setattr(
        webcam.server.http_server.requests,
        'post',
        lambda url, files, *a, **k: MockPostRequest(status=404)
    )
    server = HttpServer({'url': 'test', 'max_photos': 1})
    with pytest.raises(ServerError) as e:
        server.upload_picture(str(tmpdir/'test.jpg'), 'IMAGE', "JPEG")
        assert "The server replied with status code 404 (TEST REASON)"
    assert len(logs) == 0


def test_upload_picture_json_error(monkeypatch, tmpdir, logs):
    image = Image.new("RGB", (100, 100), color="#FFFFFF")
    image.save(str(tmpdir/'test.jpg'))

    monkeypatch.setattr(
        webcam.server.http_server.requests,
        'post',
        lambda url, files, *a, **k: MockPostRequest(response="hello")
    )
    server = HttpServer({'url': 'test', 'max_photos': 1})
    with pytest.raises(ServerError) as e:
        server.upload_picture(str(tmpdir/'test.jpg'), 'IMAGE', "JPEG")
        assert "The server did not reply valid JSON."
    assert len(logs) == 0


def test_upload_picture_malformed_response_no_photo_key(monkeypatch, tmpdir, logs):
    image = Image.new("RGB", (100, 100), color="#FFFFFF")
    image.save(str(tmpdir/'test.jpg'))

    monkeypatch.setattr(
        webcam.server.http_server.requests,
        'post',
        lambda url, files, *a, **k: MockPostRequest(response="{}")
    )
    server = HttpServer({'url': 'test', 'max_photos': 1})
    with pytest.raises(ServerError) as e:
        server.upload_picture(str(tmpdir/'test.jpg'), 'IMAGE', "JPEG")
        assert "The server reply was unexpected: "\
               "the image probably didn't arrive" in str(e)
    assert len(logs) == 0


def test_upload_picture_remote_exception_in_photo_key(monkeypatch, tmpdir, logs):
    image = Image.new("RGB", (100, 100), color="#FFFFFF")
    image.save(str(tmpdir/'test.jpg'))

    monkeypatch.setattr(
        webcam.server.http_server.requests,
        'post',
        lambda url, files, *a, **k: MockPostRequest(response="{'photo': 'test error!'}")
    )
    server = HttpServer({'url': 'test', 'max_photos': 1})
    with pytest.raises(ServerError) as e:
        server.upload_picture(str(tmpdir/'test.jpg'), 'IMAGE', "JPEG")
        assert "The server reply was unexpected: "\
               "the image probably didn't arrive" in str(e)
        assert "test error!" in str(e)
    assert len(logs) == 0
