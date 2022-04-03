from textwrap import dedent
from freezegun import freeze_time

import zanzocam.webcam as webcam
import zanzocam.constants as constants
from zanzocam.webcam.main import main
from tests.conftest import in_logs

# Try to import PiCamera - unless you're running on a RPi, 
# this won't work and a mock is loaded instead
try:
    from picamera import PiCamera
except ImportError as e:
    from tests.conftest import MockPiCamera as PiCamera
    webcam.camera.PiCamera = PiCamera



@freeze_time("2021-01-01 10:00:00")
def test_same_config_on_ftp(logs):
    """
        In this test:
            - Everything works as expected, no errors
            - The downloaded config is identical to the existing one
            - It's daytime and in working hours
            - Pictures are shot with a real PiCamera if possible, so
                the actual need for multiple shots depends on the
                luminance of the real picture. 
                If mocked, the mocked image is daylight bright.
            - The images are shot every hour
            - The connection to the server is done in FTP with TLS
            - The image has overlays
    """
    with open(constants.CONFIGURATION_FILE, 'w') as c:
        c.write(dedent("""\
        {
            "server": {
                "protocol": "ftp",
                "hostname": "test-hostname.test",
                "username": "me",
                "password": "secret",
                "max_photos": "1"
            },
            "time": {
                "start_activity": "07:00",
                "stop_activity": "21:00",
                "frequency": "60"
            },
            "image": {
                "name": "image",
                "extension": "jpg",
                "width": "3280",
                "height": "2464",
                "hor_flip": "false",
                "ver_flip": "true",
                "background_color": "#FFFF00",
                "date_format": "%A, %d %B %Y",
                "time_format": "%H:%M"
            },
            "overlays": {
                "top_left": {
                    "type": "text",
                    "text": "%%DATE %%TIME",
                    "font_size": "30",
                    "over_the_picture": "false",
                    "font_color": "#FFFFFF",
                    "background_color": "#00000088"
                },
                "bottom_center": {
                    "type": "image",
                    "path": "test_image.png",
                    "over_the_picture": "true"
                }
            }
        }
        """))
    main()
    assert in_logs(logs, "Execution completed successfully")
    assert not in_logs(logs, "Traceback (most recent call last):")


@freeze_time("2021-01-01 10:00:00")
def test_same_config_on_http(logs):
    """
        In this test:
            - Everything works as expected, no errors
            - The downloaded config is identical to the existing one
            - It's daytime and in working hours
            - Pictures are shot with a real PiCamera if possible, so
                the actual need for multiple shots depends on the
                luminance of the real picture. 
                If mocked, the mocked image is fully red, so it should
                be detected as bright
            - The images are shot every hour
            - The connection to the server is done in HTTP
            - The image has overlays
            - Overall this config relies more on default values than the above one
    """
    with open(constants.CONFIGURATION_FILE, 'w') as c:
        c.write(dedent("""\
        {
            "server": {
                "protocol": "http",
                "url": "https://test-url.test",
                "username": "me",
                "password": "secret",
                "max_photos": "1"
            },
            "time": {
                "start_activity": "07:00",
                "stop_activity": "21:00",
                "frequency": "60"
            },
            "image": {
                "name": "image",
                "extension": "jpg",
                "width": "3280",
                "height": "2464",
                "background_color": "#FFFF00"
            },
            "overlays": {
                "bottom_left": {
                    "type": "image",
                    "path": "test_image.gif",
                    "over_the_picture": "false"
                },
                "top_right": {
                    "type": "text",
                    "text": "%%DATE, %%TIME",
                    "font_size": "5",
                    "over_the_picture": "true"
                }
            }
        }
        """))
    main()
    assert in_logs(logs, "Execution completed successfully")
    assert not in_logs(logs, "Traceback (most recent call last):")


@freeze_time("2021-01-01 00:00:00")
def test_night_time(logs):
    """
        In this test:
            - Everything works as expected, no errors
            - It's out of working hours, so nothing really happens
    """
    with open(constants.CONFIGURATION_FILE, 'w') as c:
        c.write(dedent("""\
        {
            "server": {
                "protocol": "ftp",
                "hostname": "test-hostname.test",
                "username": "me",
                "password": "secret",
                "max_photos": "1"
            },
            "time": {
                "start_activity": "07:00",
                "stop_activity": "21:00",
                "frequency": "60"
            },
            "image": {
                "name": "image",
                "extension": "jpg",
                "width": "3280",
                "height": "2464"
            }
        }
        """))
    main()
    assert in_logs(logs, "Execution completed successfully")
    assert not in_logs(logs, "Traceback (most recent call last):")
    assert not in_logs(logs, "Downloading")
    assert not in_logs(logs, "Taking picture")


@freeze_time("2021-01-01 10:00:00")
def test_no_initial_config_or_backup(logs):
    """
        In this test the user forgot to configure ZANZOCAM
        before shooting the first picture, so neither the 
        configuration file nor its backup are present.
    """
    main()
    assert in_logs(logs, "Execution completed with errors")
    assert in_logs(logs, "No configuration")
    assert in_logs(logs, "No backup configuration")
    assert not in_logs(logs, "Traceback (most recent call last):")
    
