import os
import shutil
import pytest
from pathlib import Path
from unittest import mock
from textwrap import dedent
from fractions import Fraction
from PIL import Image, ImageChops
from freezegun import freeze_time
from datetime import datetime, timedelta

import webcam
import constants
from webcam.camera import Camera
from webcam.configuration import Configuration

# Try to import PiCamera - unless you're running on a RPi, 
# this won't work and a mock is loaded instead
try:
    from picamera import PiCamera
except ImportError as e:
    from tests.conftest import MockPiCamera as PiCamera
    webcam.camera.PiCamera = PiCamera



def test_create_camera_no_dict(monkeypatch, logs):
    camera = Camera("something!")
    assert len(logs) == 1
    assert "WARNING! Image information must be a dictionary" in logs[0]
    for key, value in constants.CAMERA_DEFAULTS.items():
        assert getattr(camera, key) == value
    assert camera.overlays == {}
    assert camera.temp_photo_path
    assert camera.processed_image_path


def test_create_camera_with_defaults_only(monkeypatch, logs):
    camera = Camera({})
    assert len(logs) == 1
    assert "WARNING! No image information given" in logs[0]
    for key, value in constants.CAMERA_DEFAULTS.items():
        assert getattr(camera, key) == value
    assert camera.overlays == {}
    assert camera.temp_photo_path
    assert camera.processed_image_path


def test_create_camera_no_overlays_block(monkeypatch, logs):
    camera = Camera({'image': {}})
    assert len(logs) == 0
    for key, value in constants.CAMERA_DEFAULTS.items():
        assert getattr(camera, key) == value
    assert camera.overlays == {}
    assert camera.temp_photo_path
    assert camera.processed_image_path


def test_create_camera_with_overlays_block(monkeypatch, logs):
    camera = Camera({'image': {}, 'overlays': {'test': 'data'}})
    assert len(logs) == 0
    for key, value in constants.CAMERA_DEFAULTS.items():
        assert getattr(camera, key) == value
    assert camera.overlays == {'test': 'data'}
    assert camera.temp_photo_path
    assert camera.processed_image_path


def test_prepare_camera_object_default_daylight(logs):
    camera = Camera({'image': {}})
    with camera._prepare_camera_object() as picam:
        assert len(logs) == 0
        assert isinstance(picam, PiCamera)
        assert picam.sensor_mode == 3 
        # Default framerate range is 30 FPS
        assert picam.framerate_range.low == Fraction(30, 1)
        assert picam.framerate_range.high == Fraction(30, 1)


def test_prepare_camera_object_default_extended_framerate(logs):
    camera = Camera({'image': {}})
    with camera._prepare_camera_object(expanded_framerate_range=True) as picam:
        assert len(logs) == 0
        assert isinstance(picam, PiCamera)
        assert picam.sensor_mode == 3 
        # Note: the fraction actually set might differ a bit,
        # what's important is that it can be a wider range, not a smaller one.
        assert picam.framerate_range.low <= Fraction(1, 10)
        assert picam.framerate_range.high >= Fraction(90, 1)


def test_prepare_camera_object_too_wide(logs):
    camera = Camera({'image': {}})
    camera.width = 10000000
    with camera._prepare_camera_object(expanded_framerate_range=True) as picam:
        assert len(logs) == 1
        assert "WARNING! The requested image width" in logs[0]
        assert "exceeds the maximum width resolution for this camera" in logs[0]
        assert isinstance(picam, PiCamera)
        assert picam.resolution[0] == picam.MAX_RESOLUTION.width


def test_prepare_camera_object_too_tall(logs):
    camera = Camera({'image': {}})
    camera.height = 10000000
    with camera._prepare_camera_object(expanded_framerate_range=True) as picam:
        assert len(logs) == 1
        assert "WARNING! The requested image height" in logs[0]
        assert "exceeds the maximum height resolution for this camera" in logs[0]
        assert isinstance(picam, PiCamera)
        assert picam.resolution[1] == picam.MAX_RESOLUTION.height


def test_camera_capture(tmpdir, logs):
    camera = Camera({'image': {}})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    assert not os.path.exists(tmpdir / "temp_photo.jpg")
    with camera._prepare_camera_object() as picam:
        camera._camera_capture(picam)
        assert len(logs) == 2
        assert "Taking picture" in logs[0]
        assert "Picture taken" in logs[1]
        assert os.path.exists(tmpdir / "temp_photo.jpg")


def test_take_picture(monkeypatch, logs):
    camera = Camera({'image': {}})
    monkeypatch.setattr(webcam.camera.Camera, 
                        '_shoot_picture', 
                        lambda *a, **k: None)
    monkeypatch.setattr(webcam.camera.Camera,
                        '_process_picture',
                        lambda *a, **k: None)
    camera.take_picture()
    assert len(logs) == 2
    assert "Shooting picture" in logs[0]
    assert "Processing picture" in logs[1]


def test_shoot_picture_no_low_light_check(tmpdir, logs):
    camera = Camera({'image': {}})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    assert not os.path.exists(tmpdir / "temp_photo.jpg")
    camera._shoot_picture()
    assert len(logs) == 4
    assert "Camera warm-up" in logs[0]
    assert "Taking picture" in logs[1]
    assert "Picture taken" in logs[2]
    assert "Luminance won't be checked" in logs[3]
    assert os.path.exists(tmpdir / "temp_photo.jpg")


def test_shoot_picture_no_low_light_check(tmpdir, logs):
    camera = Camera({'image': {}})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    camera.use_low_light_algorithm = False
    camera._shoot_picture()
    assert len(logs) == 4
    assert "Camera warm-up" in logs[0]
    assert "Taking picture" in logs[1]
    assert "Picture taken" in logs[2]
    assert "Luminance won't be checked" in logs[3]


def test_shoot_picture_daylight_luminance(monkeypatch, tmpdir, logs):
    camera = Camera({'image': {}})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"

    monkeypatch.setattr(webcam.camera.Camera, 
                        '_luminance_from_path', 
                        lambda *a: constants.MINIMUM_DAYLIGHT_LUMINANCE + 10)

    camera._shoot_picture()
    assert len(logs) == 4
    assert "Camera warm-up" in logs[0]
    assert "Taking picture" in logs[1]
    assert "Picture taken" in logs[2]
    assert "Daylight luminance detected" in logs[3]


def test_shoot_picture_low_light_luminance_no_settle(monkeypatch, tmpdir, logs):
    camera = Camera({'image': {}})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    camera.let_awb_settle_in_dark = False

    monkeypatch.setattr(webcam.camera.Camera, 
                        '_luminance_from_path', 
                        lambda *a, **k: constants.MINIMUM_DAYLIGHT_LUMINANCE - 10)
    monkeypatch.setattr(webcam.camera.Camera,
                        '_low_light_search',
                        lambda *a, **k: (constants.MINIMUM_DAYLIGHT_LUMINANCE, 1, 1, 1))

    camera._shoot_picture()
    assert len(logs) == 4
    assert "Camera warm-up" in logs[0]
    assert "Taking picture" in logs[1]
    assert "Picture taken" in logs[2]
    assert "No final picture will be taken" in logs[3]


def test_shoot_picture_low_light_luminance_with_settle(monkeypatch, tmpdir, logs):
    camera = Camera({'image': {}})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"

    monkeypatch.setattr(webcam.camera.Camera, 
                        '_luminance_from_path', 
                        lambda *a, **k: constants.MINIMUM_DAYLIGHT_LUMINANCE - 10)
    monkeypatch.setattr(webcam.camera.Camera,
                        '_low_light_search',
                        lambda *a, **k: (constants.MINIMUM_DAYLIGHT_LUMINANCE, 1, 1, 1))

    camera._shoot_picture()
    assert len(logs) == 8
    assert "Camera warm-up" in logs[0]
    assert "Taking picture" in logs[1]
    assert "Picture taken" in logs[2]
    assert "Taking one more picture with the final parameters" in logs[3]
    assert "Adjusting white balance" in logs[4]
    assert "Taking picture" in logs[5]
    assert "Picture taken" in logs[6]
    assert "Final luminance" in logs[7]


def test_low_light_search_twilight_three_attempts(monkeypatch, tmpdir, logs):
    camera = Camera({'image': {}})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    
    monkeypatch.setattr(webcam.camera.Camera,
                        "_camera_capture",
                        lambda *a, **k: None)

    monkeypatch.setattr(webcam.camera.Camera, 
                        '_luminance_from_path', 
                        mock.Mock(side_effect=[
                            constants.MINIMUM_DAYLIGHT_LUMINANCE + 10,
                            constants.MINIMUM_DAYLIGHT_LUMINANCE - 10,
                            constants.MINIMUM_DAYLIGHT_LUMINANCE,
                        ]))
    monkeypatch.setattr(webcam.camera.Camera,
                        '_compute_target_luminance',
                        lambda *a, **k: constants.MINIMUM_DAYLIGHT_LUMINANCE)

    camera._low_light_search(constants.MINIMUM_DAYLIGHT_LUMINANCE - 10)
    assert len(logs) == 6
    assert "Low light detected" in logs[0]
    assert "Trying to get a brighter image" in logs[1]
    assert "Camera warm-up" in logs[2]
    assert "bright. Luminance achieved" in logs[3]
    assert "dark. Luminance achieved" in logs[4]
    assert "OK! Luminance achieved" in logs[5]


def test_low_light_search_initial_picture_very_dark(monkeypatch, tmpdir, logs):
    camera = Camera({'image': {}})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    
    monkeypatch.setattr(webcam.camera.Camera,
                        "_camera_capture",
                        lambda *a, **k: None)

    monkeypatch.setattr(webcam.camera.Camera, 
                        '_luminance_from_path', 
                        lambda *a, **k: constants.MINIMUM_DAYLIGHT_LUMINANCE)

    monkeypatch.setattr(webcam.camera.Camera,
                        '_compute_target_luminance',
                        lambda *a, **k: constants.MINIMUM_DAYLIGHT_LUMINANCE)

    camera._low_light_search(constants.NO_LUMINANCE_THRESHOLD - 1)
    assert len(logs) == 5
    assert "Low light detected" in logs[0]
    assert "Trying to get a brighter image" in logs[1]
    assert "Luminance is below " in logs[2]
    assert "Camera warm-up" in logs[3]
    assert "OK! Luminance achieved" in logs[4]


def test_low_light_search_one_attempt_returns_a_black_frame(monkeypatch, tmpdir, logs):
    camera = Camera({'image': {}})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    
    monkeypatch.setattr(webcam.camera.Camera,
                        "_camera_capture",
                        lambda *a, **k: None)

    monkeypatch.setattr(webcam.camera.Camera, 
                        '_luminance_from_path', 
                        mock.Mock(side_effect=[
                            0.0,
                            constants.MINIMUM_DAYLIGHT_LUMINANCE,
                        ]))

    monkeypatch.setattr(webcam.camera.Camera,
                        '_compute_target_luminance',
                        lambda *a, **k: constants.MINIMUM_DAYLIGHT_LUMINANCE)

    camera._low_light_search(constants.MINIMUM_DAYLIGHT_LUMINANCE - 10)
    assert len(logs) == 5
    assert "Low light detected" in logs[0]
    assert "Trying to get a brighter image" in logs[1]
    assert "Camera warm-up" in logs[2]
    assert "The camera shot a fully black picture" in logs[3]
    assert "OK! Luminance achieved" in logs[4]


def test_low_light_attempts_are_limited(monkeypatch, tmpdir, logs):
    camera = Camera({'image': {}})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    
    monkeypatch.setattr(webcam.camera.Camera,
                        "_camera_capture",
                        lambda *a, **k: None)

    monkeypatch.setattr(webcam.camera.Camera, 
                        '_luminance_from_path', 
                        lambda *a, **k: constants.MINIMUM_DAYLIGHT_LUMINANCE - 10)

    monkeypatch.setattr(webcam.camera.Camera,
                        '_compute_target_luminance',
                        lambda *a, **k: constants.MINIMUM_DAYLIGHT_LUMINANCE)

    camera._low_light_search(constants.MINIMUM_DAYLIGHT_LUMINANCE - 10)
    assert "Low light detected" in logs[0]
    assert "Trying to get a brighter image" in logs[1]
    assert "Camera warm-up" in logs[2]
    for i in range(8):
        assert "dark. Luminance achieved" in logs[3+i]
    assert "The low light algorithm failed!" in logs[12]
    

def test_low_light_shutter_speed_and_ISO_are_limited(monkeypatch, tmpdir, logs):
    camera = Camera({'image': {}})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    
    monkeypatch.setattr(webcam.camera.Camera,
                        "_camera_capture",
                        lambda *a, **k: None)

    monkeypatch.setattr(webcam.camera.Camera, 
                        '_luminance_from_path', 
                        lambda *a, **k: constants.MINIMUM_DAYLIGHT_LUMINANCE - 10)

    # This makes _low_light_equation return a crazy high number
    monkeypatch.setattr(webcam.camera.Camera,
                        '_compute_target_luminance',
                        lambda *a, **k: constants.MAX_SHUTTER_SPEED)

    camera._low_light_search(constants.MINIMUM_DAYLIGHT_LUMINANCE - 10)
    assert "Low light detected" in logs[0]
    assert "Trying to get a brighter image" in logs[1]
    assert "Camera warm-up" in logs[2]
    assert "dark. Luminance achieved" in logs[3]
    assert "Max shutter speed has been reached" in logs[4]
    assert "dark. Luminance achieved" in logs[5]
    assert "Not allowed to raise the shutter speed further" in logs[6]
    assert "Max shutter speed has been reached" in logs[7]
    assert "dark. Luminance achieved" in logs[8]
    assert "ISO is at 800 and shutter speed is at max" in logs[9]
    

def test_compute_target_luminance_daylight(logs):
    camera = Camera({'image': {}})
    lum = constants.MINIMUM_DAYLIGHT_LUMINANCE + 10
    assert camera._compute_target_luminance(lum) == lum
    assert len(logs) == 0


def test_compute_target_luminance_night_upper_bound_check(logs):
    camera = Camera({'image': {}})
    lum = constants.MINIMUM_DAYLIGHT_LUMINANCE
    assert camera._compute_target_luminance(lum) == constants.MINIMUM_DAYLIGHT_LUMINANCE
    assert len(logs) == 0


def test_compute_target_luminance_night_intermediate_check(logs):
    camera = Camera({'image': {}})
    lum = constants.MINIMUM_DAYLIGHT_LUMINANCE - 10
    assert camera._compute_target_luminance(lum) <= constants.MINIMUM_DAYLIGHT_LUMINANCE
    assert camera._compute_target_luminance(lum) >= constants.MINIMUM_NIGHT_LUMINANCE
    assert len(logs) == 0


def test_compute_target_luminance_night_lower_bound_check(logs):
    camera = Camera({'image': {}})
    lum = 0
    assert camera._compute_target_luminance(lum) == constants.MINIMUM_NIGHT_LUMINANCE
    assert len(logs) == 0


def test_luminance_from_path_white_pic(tmpdir, logs):
    camera = Camera({'image': {}})
    image = Image.new("RGB", (10, 10), color="#ffffff")
    image.save(str(tmpdir / 'pic.jpg'), format="JPEG")
    assert camera._luminance_from_path(tmpdir / 'pic.jpg') > constants.MINIMUM_DAYLIGHT_LUMINANCE
    assert len(logs) == 0


def test_luminance_from_path_black_pic(tmpdir, logs):
    camera = Camera({'image': {}})
    image = Image.new("RGB", (10, 10), color="#000000")
    image.save(str(tmpdir / 'pic.jpg'), format="JPEG")
    assert camera._luminance_from_path(tmpdir / 'pic.jpg') < constants.NO_LUMINANCE_THRESHOLD
    assert len(logs) == 0


def test_process_picture_cant_open_picture(tmpdir, logs):
    camera = Camera({'image': {}})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    
    camera._process_picture()

    assert len(logs) == 1
    assert "Failed to open the image for editing" in logs[0]
    assert not os.path.exists(camera.temp_photo_path)


def test_process_picture_no_overlays_all_defaults(mock_piexif, tmpdir, logs):
    camera = Camera({'image': {}})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    image = Image.new("RGB", (100, 100), color="#000000")
    image.save(str(camera.temp_photo_path))

    camera._process_picture()

    assert len(logs) == 0
    assert os.path.isfile(camera.temp_photo_path)    
    assert os.path.isfile(camera.processed_image_path)
    assert str(camera.processed_image_path).endswith("jpg")
    temp_img = Image.open(str(camera.temp_photo_path))
    proc_img = Image.open(str(camera.processed_image_path))
    assert not ImageChops.difference(temp_img, proc_img).getbbox()


def test_process_picture_no_overlays_save_in_png(tmpdir, logs):
    camera = Camera({'image': {'extension': 'png'}})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    image = Image.new("RGB", (10, 10), color="#000000")
    image.save(str(camera.temp_photo_path))

    camera._process_picture()

    assert len(logs) == 0
    assert os.path.exists(camera.temp_photo_path)    
    assert os.path.exists(camera.processed_image_path)
    assert str(camera.processed_image_path).endswith("png")
    temp_img = Image.open(str(camera.temp_photo_path))
    proc_img = Image.open(str(camera.processed_image_path))
    assert not ImageChops.difference(temp_img, proc_img.convert("RGB")).getbbox()


def test_process_picture_no_overlays_save_in_gif(tmpdir, logs):
    camera = Camera({'image': {'extension': 'gif'}})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    image = Image.new("RGB", (10, 10), color="#000000")
    image.save(str(camera.temp_photo_path))

    camera._process_picture()

    assert len(logs) == 0
    assert os.path.exists(camera.temp_photo_path)    
    assert os.path.exists(camera.processed_image_path)
    assert str(camera.processed_image_path).endswith("gif")
    temp_img = Image.open(str(camera.temp_photo_path))
    proc_img = Image.open(str(camera.processed_image_path))
    assert not ImageChops.difference(temp_img, proc_img.convert("RGB")).getbbox()


def test_process_picture_no_overlays_exif_fails(monkeypatch, tmpdir, logs):
    camera = Camera({'image': {}})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    image = Image.new("RGB", (100, 100), color="#000000")
    image.save(str(camera.temp_photo_path))

    monkeypatch.setattr(
        webcam.camera.piexif,
        'load',
        lambda *a, **k: 1/0
    )

    camera._process_picture()

    assert len(logs) == 1
    assert "Failed to copy EXIF information" in logs[0]
    assert os.path.isfile(camera.temp_photo_path)    
    assert os.path.isfile(camera.processed_image_path)
    assert str(camera.processed_image_path).endswith("jpg")
    temp_img = Image.open(str(camera.temp_photo_path))
    proc_img = Image.open(str(camera.processed_image_path))
    assert not ImageChops.difference(temp_img, proc_img).getbbox()


def test_process_picture_overlay_fails(monkeypatch, tmpdir, logs):
    camera = Camera({'image': {}, 'overlays': {'test': {}}})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    image = Image.new("RGB", (10, 10), color="#000000")
    image.save(str(camera.temp_photo_path))

    monkeypatch.setattr(webcam.camera.Overlay,
                        "__init__",
                        lambda *a, **k: 1/0)

    camera._process_picture()

    assert len(logs) == 1
    assert "This overlay will be skipped" in logs[0]
    assert os.path.exists(camera.temp_photo_path)    
    assert os.path.exists(camera.processed_image_path)
    temp_img = Image.open(str(camera.temp_photo_path))
    proc_img = Image.open(str(camera.processed_image_path))
    assert not ImageChops.difference(temp_img, proc_img).getbbox()


def test_process_overlay_of_wrong_position(monkeypatch, tmpdir, logs):
    camera = Camera({'image': {}, 'overlays': {'test': {}}})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    image = Image.new("RGB", (10, 10), color="#000000")
    image.save(str(camera.temp_photo_path))

    camera._process_picture()

    assert len(logs) == 2
    assert "Creating overlay" in logs[0]
    assert "The position of this overlay (test) is malformed" in logs[1]
    assert "This overlay will be skipped" in logs[1]
    assert os.path.exists(camera.temp_photo_path)    
    assert os.path.exists(camera.processed_image_path)
    temp_img = Image.open(str(camera.temp_photo_path))
    proc_img = Image.open(str(camera.processed_image_path))
    assert not ImageChops.difference(temp_img, proc_img).getbbox()


def test_process_overlay_with_no_type(monkeypatch, tmpdir, logs):
    camera = Camera({'image': {}, 'overlays': {'top_right': {}}})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    image = Image.new("RGB", (10, 10), color="#000000")
    image.save(str(camera.temp_photo_path))

    camera._process_picture()

    assert len(logs) == 2
    assert "Creating overlay" in logs[0]
    assert "Overlay type not specified for position" in logs[1]
    assert "This overlay will be skipped" in logs[1]
    assert os.path.exists(camera.temp_photo_path)    
    assert os.path.exists(camera.processed_image_path)
    temp_img = Image.open(str(camera.temp_photo_path))
    proc_img = Image.open(str(camera.processed_image_path))
    assert not ImageChops.difference(temp_img, proc_img).getbbox()


def test_process_overlay_with_wrong_type(monkeypatch, tmpdir, logs):
    camera = Camera({'image': {}, 'overlays': {'top_right': {'type': 'test'}}})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    image = Image.new("RGB", (10, 10), color="#000000")
    image.save(str(camera.temp_photo_path))

    camera._process_picture()

    assert len(logs) == 2
    assert "Creating overlay" in logs[0]
    assert "Overlay type 'test' not recognized" in logs[1]
    assert "This overlay will be skipped" in logs[1]
    assert os.path.exists(camera.temp_photo_path)    
    assert os.path.exists(camera.processed_image_path)
    temp_img = Image.open(str(camera.temp_photo_path))
    proc_img = Image.open(str(camera.processed_image_path))
    assert not ImageChops.difference(temp_img, proc_img).getbbox()


def test_process_picture_overlay_into_picture(tmpdir, logs):
    camera = Camera({'image': {}, 'overlays': {
        'top_right': {
            'type': 'image',
            'path': tmpdir / 'overlay.png',
            'over_the_picture': True,
        },
        'bottom_left': {
            'type': 'image',
            'path': tmpdir / 'overlay.png',
            'over_the_picture': True,
        }
    }})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    image = Image.new("RGB", (10, 10), color="#000000")
    image.save(str(camera.temp_photo_path))

    overlay_image = Image.new("RGBA", (5, 5), color="#FFFFFF99")
    overlay_image.save(str(tmpdir / 'overlay.png'))

    camera._process_picture()

    assert len(logs) == 2
    assert "Creating overlay" in logs[0]
    assert "Creating overlay" in logs[1]
    assert os.path.exists(camera.temp_photo_path)    
    assert os.path.exists(camera.processed_image_path)
    temp_img = Image.open(str(camera.temp_photo_path))
    proc_img = Image.open(str(camera.processed_image_path))
    assert ImageChops.difference(temp_img, proc_img).getbbox()
    assert temp_img.width == proc_img.width
    assert temp_img.height == proc_img.height


def test_process_text_overlay_into_picture(tmpdir, logs):
    camera = Camera({'image': {}, 'overlays': {
        'top_right': {
            'type': 'text',
            'text': "Hello",
            'over_the_picture': True,
        }
    }})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    image = Image.new("RGB", (100, 100), color="#FFFFFF")
    image.save(str(camera.temp_photo_path))

    camera._process_picture()

    assert len(logs) == 1
    assert "Creating overlay" in logs[0]
    assert os.path.exists(camera.temp_photo_path)    
    assert os.path.exists(camera.processed_image_path)
    temp_img = Image.open(str(camera.temp_photo_path))
    proc_img = Image.open(str(camera.processed_image_path))
    assert ImageChops.difference(temp_img, proc_img).getbbox()
    assert temp_img.width == proc_img.width
    assert temp_img.height == proc_img.height


def test_process_text_overlay_out_of_picture(tmpdir, logs):
    camera = Camera({'image': {}, 'overlays': {
        'top_right': {
            'type': 'text',
            'text': "Hello",
            'over_the_picture': False,
        }
    }})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    image = Image.new("RGB", (100, 100), color="#FFFFFF")
    image.save(str(camera.temp_photo_path))

    camera._process_picture()

    assert len(logs) == 1
    assert "Creating overlay" in logs[0]
    assert os.path.exists(camera.temp_photo_path)    
    assert os.path.exists(camera.processed_image_path)
    temp_img = Image.open(str(camera.temp_photo_path))
    proc_img = Image.open(str(camera.processed_image_path))
    assert ImageChops.difference(temp_img, proc_img).getbbox()
    assert temp_img.width == proc_img.width
    assert temp_img.height < proc_img.height # TODO Test better...


def test_process_long_text_overlay_out_of_picture(tmpdir, logs):
    camera = Camera({'image': {}, 'overlays': {
        'top_right': {
            'type': 'text',
            'text': "Hello hello hello hello hello hello hello hello",
            'over_the_picture': False,
        }
    }})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    image = Image.new("RGB", (100, 100), color="#FFFFFF")
    image.save(str(camera.temp_photo_path))

    camera._process_picture()

    assert len(logs) == 1
    assert "Creating overlay" in logs[0]
    assert os.path.exists(camera.temp_photo_path)    
    assert os.path.exists(camera.processed_image_path)
    temp_img = Image.open(str(camera.temp_photo_path))
    proc_img = Image.open(str(camera.processed_image_path))
    assert ImageChops.difference(temp_img, proc_img).getbbox()
    assert temp_img.width == proc_img.width
    assert temp_img.height < proc_img.height # TODO Test better...


def test_process_picture_overlay_missing_file(tmpdir, logs):
    camera = Camera({'image': {}, 'overlays': {
        'top_right': {
            'type': 'image',
            'path': tmpdir / 'overlay.png',
        }
    }})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    image = Image.new("RGB", (10, 10), color="#000000")
    image.save(str(camera.temp_photo_path))

    camera._process_picture()

    assert len(logs) == 2
    assert "Creating overlay" in logs[0]
    assert "can't be found or is impossible to open. " \
           "This overlay will be skipped" in logs[1]
    assert os.path.exists(camera.temp_photo_path)    
    assert os.path.exists(camera.processed_image_path)
    temp_img = Image.open(str(camera.temp_photo_path))
    proc_img = Image.open(str(camera.processed_image_path))
    assert not ImageChops.difference(temp_img, proc_img).getbbox()


def test_process_picture_overlay_out_of_picture_both_above(tmpdir, logs):
    camera = Camera({'image': {}, 'overlays': {
        'top_right': {
            'type': 'image',
            'path': tmpdir / 'overlay1.png',
            'over_the_picture': False,
            'padding_ratio': 0
        },
        'top_center': {
            'type': 'image',
            'path': tmpdir / 'overlay2.png',
            'over_the_picture': False,
            'padding_ratio': 0
        }
    }})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    image = Image.new("RGB", (10, 10), color="#000000")
    image.save(str(camera.temp_photo_path))

    overlay_image = Image.new("RGBA", (5, 5), color="#FFFFFF99")
    overlay_image.save(str(tmpdir / 'overlay1.png'))
    overlay_image = Image.new("RGBA", (3, 3), color="#FFFFFF99")
    overlay_image.save(str(tmpdir / 'overlay2.png'))

    camera._process_picture()

    assert len(logs) == 2
    assert "Creating overlay" in logs[0]
    assert "Creating overlay" in logs[1]
    assert os.path.exists(camera.temp_photo_path)    
    assert os.path.exists(camera.processed_image_path)
    temp_img = Image.open(str(camera.temp_photo_path))
    proc_img = Image.open(str(camera.processed_image_path))
    assert ImageChops.difference(temp_img, proc_img).getbbox()
    assert proc_img.width == 10
    assert temp_img.width == proc_img.width
    assert temp_img.height != proc_img.height
    assert proc_img.height == 15


def test_process_picture_overlay_out_of_picture_above_and_below(tmpdir, logs):
    camera = Camera({'image': {}, 'overlays': {
        'top_left': {
            'type': 'image',
            'path': tmpdir / 'overlay1.png',
            'over_the_picture': False,
            'padding_ratio': 0
        },
        'bottom_center': {
            'type': 'image',
            'path': tmpdir / 'overlay2.png',
            'over_the_picture': False,
            'padding_ratio': 0
        }
    }})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    image = Image.new("RGB", (10, 10), color="#000000")
    image.save(str(camera.temp_photo_path))

    overlay_image = Image.new("RGBA", (5, 5), color="#FFFFFF99")
    overlay_image.save(str(tmpdir / 'overlay1.png'))
    overlay_image = Image.new("RGBA", (3, 3), color="#FFFFFF99")
    overlay_image.save(str(tmpdir / 'overlay2.png'))

    camera._process_picture()

    assert len(logs) == 2
    assert "Creating overlay" in logs[0]
    assert "Creating overlay" in logs[1]
    assert os.path.exists(camera.temp_photo_path)    
    assert os.path.exists(camera.processed_image_path)
    temp_img = Image.open(str(camera.temp_photo_path))
    proc_img = Image.open(str(camera.processed_image_path))
    assert ImageChops.difference(temp_img, proc_img).getbbox()
    assert proc_img.width == 10
    assert temp_img.width == proc_img.width
    assert temp_img.height != proc_img.height
    assert proc_img.height == 18


def test_process_picture_overlay_negative_margin_on_picture(tmpdir, logs):
    camera = Camera({'image': {}, 'overlays': {
        'top_left': {
            'type': 'image',
            'path': tmpdir / 'overlay.png',
            'over_the_picture': True,
            'padding_ratio': -0.2
        }
    }})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    image = Image.new("RGB", (10, 10), color="#000000")
    image.save(str(camera.temp_photo_path))

    overlay_image = Image.new("RGBA", (25, 5), color="#FFFFFF99")
    overlay_image.save(str(tmpdir / 'overlay.png'))

    camera._process_picture()

    assert len(logs) == 2
    assert "Creating overlay" in logs[0]
    assert "This overlay exceeds the margin of the image itself " \
           "on the right" in logs[1]
    assert os.path.exists(camera.temp_photo_path)    
    assert os.path.exists(camera.processed_image_path)
    temp_img = Image.open(str(camera.temp_photo_path))
    proc_img = Image.open(str(camera.processed_image_path))
    assert ImageChops.difference(temp_img, proc_img).getbbox()
    assert temp_img.width == proc_img.width
    assert temp_img.height == proc_img.height


def test_process_picture_overlay_negative_margin_out_of_picture(tmpdir, logs):
    camera = Camera({'image': {}, 'overlays': {
        'top_right': {
            'type': 'image',
            'path': tmpdir / 'overlay.png',
            'over_the_picture': False,
            'padding_ratio': -0.2
        }
    }})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    image = Image.new("RGB", (10, 10), color="#000000")
    image.save(str(camera.temp_photo_path))

    overlay_image = Image.new("RGBA", (25, 5), color="#FFFFFF99")
    overlay_image.save(str(tmpdir / 'overlay.png'))

    camera._process_picture()

    assert len(logs) == 2
    assert "Creating overlay" in logs[0]
    assert "This overlay exceeds the margin of the image itself " \
           "on the left" in logs[1]
    assert os.path.exists(camera.temp_photo_path)    
    assert os.path.exists(camera.processed_image_path)
    temp_img = Image.open(str(camera.temp_photo_path))
    proc_img = Image.open(str(camera.processed_image_path))
    assert ImageChops.difference(temp_img, proc_img).getbbox()
    assert temp_img.width == proc_img.width
    assert temp_img.height + 3 == proc_img.height


def test_process_picture_overlay_negative_position_on_picture(monkeypatch, tmpdir, logs):
    camera = Camera({'image': {}, 'overlays': {
        'top_left': {
            'type': 'image',
            'path': tmpdir / 'overlay.png',
            'over_the_picture': True,
            'padding_ratio': -0.2
        }
    }})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    image = Image.new("RGB", (10, 10), color="#000000")
    image.save(str(camera.temp_photo_path))

    overlay_image = Image.new("RGBA", (5, 5), color="#FFFFFF99")
    overlay_image.save(str(tmpdir / 'overlay.png'))

    monkeypatch.setattr(webcam.camera.Overlay,
                        "compute_position",
                        lambda *a, **k: (-2, -2))

    camera._process_picture()

    assert len(logs) == 3
    assert "Creating overlay" in logs[0]
    assert "This overlay exceeds the margin of the image itself " \
           "on the left" in logs[1]
    assert "This overlay exceeds the margin of the image itself " \
           "at the top" in logs[2]
    assert os.path.exists(camera.temp_photo_path)    
    assert os.path.exists(camera.processed_image_path)
    temp_img = Image.open(str(camera.temp_photo_path))
    proc_img = Image.open(str(camera.processed_image_path))
    assert ImageChops.difference(temp_img, proc_img).getbbox()
    assert temp_img.width == proc_img.width
    assert temp_img.height == proc_img.height


def test_process_picture_overlay_negative_position_out_of_picture(monkeypatch, tmpdir, logs):
    camera = Camera({'image': {}, 'overlays': {
        'top_left': {
            'type': 'image',
            'path': tmpdir / 'overlay.png',
            'over_the_picture': False,
            'padding_ratio': -0.2
        }
    }})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    image = Image.new("RGB", (10, 10), color="#000000")
    image.save(str(camera.temp_photo_path))

    overlay_image = Image.new("RGBA", (5, 5), color="#FFFFFF99")
    overlay_image.save(str(tmpdir / 'overlay.png'))

    monkeypatch.setattr(webcam.camera.Overlay,
                        "compute_position",
                        lambda *a, **k: (-2, -2))

    camera._process_picture()

    assert len(logs) == 3
    assert "Creating overlay" in logs[0]
    assert "This overlay exceeds the margin of the image itself " \
           "on the left" in logs[1]
    assert "This overlay exceeds the margin of the image itself " \
           "at the top" in logs[2]
    assert os.path.exists(camera.temp_photo_path)    
    assert os.path.exists(camera.processed_image_path)
    temp_img = Image.open(str(camera.temp_photo_path))
    proc_img = Image.open(str(camera.processed_image_path))
    assert ImageChops.difference(temp_img, proc_img).getbbox()
    assert temp_img.width == proc_img.width
    assert temp_img.height + 3 == proc_img.height


def test_process_picture_overlay_too_wide_on_picture(tmpdir, logs):
    camera = Camera({'image': {}, 'overlays': {
        'top_left': {
            'type': 'image',
            'path': tmpdir / 'overlay.png',
            'over_the_picture': True,
            'padding_ratio': 0
        }
    }})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    image = Image.new("RGB", (10, 10), color="#000000")
    image.save(str(camera.temp_photo_path))

    overlay_image = Image.new("RGBA", (25, 5), color="#FFFFFF99")
    overlay_image.save(str(tmpdir / 'overlay.png'))

    camera._process_picture()

    assert len(logs) == 2
    assert "Creating overlay" in logs[0]
    assert "This overlay exceeds the margin of the image itself " \
           "on the right" in logs[1]
    assert os.path.exists(camera.temp_photo_path)    
    assert os.path.exists(camera.processed_image_path)
    temp_img = Image.open(str(camera.temp_photo_path))
    proc_img = Image.open(str(camera.processed_image_path))
    assert ImageChops.difference(temp_img, proc_img).getbbox()
    assert temp_img.width == proc_img.width
    assert temp_img.height == proc_img.height


def test_process_picture_overlay_too_wide_out_of_picture(tmpdir, logs):
    camera = Camera({'image': {}, 'overlays': {
        'top_left': {
            'type': 'image',
            'path': tmpdir / 'overlay.png',
            'over_the_picture': False,
            'padding_ratio': 0
        }
    }})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    image = Image.new("RGB", (10, 10), color="#000000")
    image.save(str(camera.temp_photo_path))

    overlay_image = Image.new("RGBA", (25, 5), color="#FFFFFF99")
    overlay_image.save(str(tmpdir / 'overlay.png'))

    camera._process_picture()

    assert len(logs) == 2
    assert "Creating overlay" in logs[0]
    assert "This overlay exceeds the margin of the image itself " \
           "on the right" in logs[1]
    assert os.path.exists(camera.temp_photo_path)    
    assert os.path.exists(camera.processed_image_path)
    temp_img = Image.open(str(camera.temp_photo_path))
    proc_img = Image.open(str(camera.processed_image_path))
    assert ImageChops.difference(temp_img, proc_img).getbbox()
    assert temp_img.width == proc_img.width
    assert temp_img.height + overlay_image.height == proc_img.height


def test_process_picture_overlay_too_tall_on_picture(tmpdir, logs):
    camera = Camera({'image': {}, 'overlays': {
        'top_left': {
            'type': 'image',
            'path': tmpdir / 'overlay.png',
            'over_the_picture': True,
            'padding_ratio': 0
        }
    }})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    image = Image.new("RGB", (10, 10), color="#000000")
    image.save(str(camera.temp_photo_path))

    overlay_image = Image.new("RGBA", (5, 25), color="#FFFFFF99")
    overlay_image.save(str(tmpdir / 'overlay.png'))

    camera._process_picture()

    assert len(logs) == 2
    assert "Creating overlay" in logs[0]
    assert "This overlay exceeds the margin of the image itself " \
           "at the bottom" in logs[1]
    assert os.path.exists(camera.temp_photo_path)    
    assert os.path.exists(camera.processed_image_path)
    temp_img = Image.open(str(camera.temp_photo_path))
    proc_img = Image.open(str(camera.processed_image_path))
    assert ImageChops.difference(temp_img, proc_img).getbbox()
    assert temp_img.width == proc_img.width
    assert temp_img.height == proc_img.height


def test_process_picture_overlay_very_tall_out_of_picture(tmpdir, logs):
    camera = Camera({'image': {}, 'overlays': {
        'top_left': {
            'type': 'image',
            'path': tmpdir / 'overlay.png',
            'over_the_picture': False,
            'padding_ratio': 0
        }
    }})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    image = Image.new("RGB", (10, 10), color="#000000")
    image.save(str(camera.temp_photo_path))

    overlay_image = Image.new("RGBA", (5, 25), color="#FFFFFF99")
    overlay_image.save(str(tmpdir / 'overlay.png'))

    camera._process_picture()

    assert len(logs) == 1
    assert "Creating overlay" in logs[0]
    assert os.path.exists(camera.temp_photo_path)    
    assert os.path.exists(camera.processed_image_path)
    temp_img = Image.open(str(camera.temp_photo_path))
    proc_img = Image.open(str(camera.processed_image_path))
    assert ImageChops.difference(temp_img, proc_img).getbbox()
    assert temp_img.width == proc_img.width
    assert temp_img.height + overlay_image.height == proc_img.height 


def test_process_picture_overlay_specify_only_width(tmpdir, logs):
    camera = Camera({'image': {}, 'overlays': {
        'top_left': {
            'type': 'image',
            'path': tmpdir / 'overlay.png',
            'over_the_picture': False,
            'width': 2,
            'padding_ratio': 0,
        }
    }})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    image = Image.new("RGB", (10, 10), color="#000000")
    image.save(str(camera.temp_photo_path))

    overlay_image = Image.new("RGBA", (20, 30), color="#FFFFFF99")
    overlay_image.save(str(tmpdir / 'overlay.png'))

    camera._process_picture()

    assert len(logs) == 1
    assert "Creating overlay" in logs[0]
    assert os.path.exists(camera.temp_photo_path)    
    assert os.path.exists(camera.processed_image_path)
    temp_img = Image.open(str(camera.temp_photo_path))
    proc_img = Image.open(str(camera.processed_image_path))
    assert ImageChops.difference(temp_img, proc_img).getbbox()
    assert temp_img.width == proc_img.width
    assert temp_img.height + (overlay_image.height/10) == proc_img.height 


def test_process_picture_overlay_specify_only_height(tmpdir, logs):
    camera = Camera({'image': {}, 'overlays': {
        'top_left': {
            'type': 'image',
            'path': tmpdir / 'overlay.png',
            'over_the_picture': False,
            'height': 2,
            'padding_ratio': 0,
        }
    }})
    camera.temp_photo_path = tmpdir / "temp_photo.jpg"
    image = Image.new("RGB", (10, 10), color="#000000")
    image.save(str(camera.temp_photo_path))

    overlay_image = Image.new("RGBA", (30, 20), color="#FFFFFF99")
    overlay_image.save(str(tmpdir / 'overlay.png'))

    camera._process_picture()

    assert len(logs) == 1
    assert "Creating overlay" in logs[0]
    assert os.path.exists(camera.temp_photo_path)    
    assert os.path.exists(camera.processed_image_path)
    temp_img = Image.open(str(camera.temp_photo_path))
    proc_img = Image.open(str(camera.processed_image_path))
    assert ImageChops.difference(temp_img, proc_img).getbbox()
    assert temp_img.width == proc_img.width
    assert temp_img.height + (overlay_image.height/10) == proc_img.height 


def test_cleanup_image_files_both(tmpdir, logs):
    camera = Camera({'image': {}})
    camera.take_picture()
    logs = []

    assert os.path.isfile(camera.temp_photo_path)
    assert os.path.isfile(camera.processed_image_path)
    camera.cleanup_image_files()
    assert not os.path.exists(camera.temp_photo_path)
    assert not os.path.exists(camera.processed_image_path)
    assert len(logs) == 0
    

def test_cleanup_image_files_only_temp(tmpdir, logs):
    camera = Camera({'image': {}})
    camera.take_picture()
    os.remove(camera.processed_image_path)
    logs = []

    camera.cleanup_image_files()
    assert not os.path.exists(camera.temp_photo_path)
    assert not os.path.exists(camera.processed_image_path)
    assert len(logs) == 0


def test_cleanup_image_files_no_files(tmpdir, logs):
    camera = Camera({'image': {}})

    camera.cleanup_image_files()
    assert not os.path.exists(camera.temp_photo_path)
    assert not os.path.exists(camera.processed_image_path)
    assert len(logs) == 0
