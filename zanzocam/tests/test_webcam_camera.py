import os
import pytest
from pathlib import Path
from textwrap import dedent
from fractions import Fraction
from freezegun import freeze_time
from datetime import datetime, timedelta
from picamera import PiCamera, PiFramerateRange

import webcam
import constants
from webcam.camera import Camera
from webcam.configuration import Configuration

from tests.conftest import point_const_to_tmpdir


@pytest.fixture(autouse=True)
def point_to_tmpdir(monkeypatch, tmpdir):
    point_const_to_tmpdir([webcam.camera, webcam.configuration], monkeypatch, tmpdir)

    

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
    with camera._prepare_camera_object() as obj:
        assert len(logs) == 0
        assert isinstance(obj, PiCamera)
        assert obj.sensor_mode == 3 
        # Default framerate range is 30 FPS
        assert obj.framerate_range.low == Fraction(30, 1)
        assert obj.framerate_range.high == Fraction(30, 1)


def test_prepare_camera_object_default_extended_framerate(logs):
    camera = Camera({'image': {}})
    with camera._prepare_camera_object(expanded_framerate_range=True) as obj:
        assert len(logs) == 0
        assert isinstance(obj, PiCamera)
        assert obj.sensor_mode == 3 
        # Note: the fraction actually set might differ a bit,
        # what's important is that it can be a wider range, not a smaller one.
        assert obj.framerate_range.low <= Fraction(1, 10)
        assert obj.framerate_range.high >= Fraction(90, 1)
