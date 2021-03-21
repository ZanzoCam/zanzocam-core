from typing import Any, Dict, Tuple, Optional

import os
import math
import datetime
import textwrap
from time import sleep
from pathlib import Path
from picamera import PiCamera
from fractions import Fraction
from PIL import Image, ImageFont, ImageDraw, ImageStat

from constants import *
from webcam.utils import log, log_error
from webcam.overlays import Overlay
from webcam.configuration import Configuration 


# Default parameters for the luminance/shutterspeed interpolation curve.
# Calculated for a Raspberry Pi Camera v1.2
# They can be overridden by custom calibrated parameters.
LUM_SPEED_PARAM_A = 600000
LUM_SPEED_PARAM_B = 60000



class Camera:
    """
    Manages the pictures and graphical operations.
    """
    def __init__(self, configuration: Configuration):
        log("Initializing camera")
        
        # Populate the attributes with the 'image' data 
        if "image" not in vars(configuration).keys():
            log("WARNING! No image information present in the configuration! "
                "Please fix the error ASAP. Fallback values are being used.")
        
        for key, value in configuration.image.items():
            setattr(self, key, value)

        # Provide defaults for all the expected values of 'image'
        self.defaults = CAMERA_DEFAULTS

        # There might be no overlays
        if "overlays" in vars(configuration).keys():
            self.overlays = configuration.overlays
        else:
            self.overlays = {}
        
        # Image name
        self.temp_photo_path = DATA_PATH / ('.temp_image.' + self.extension)
        self.processed_image_path = DATA_PATH / ('.final_image.' + self.extension)

        # Check the calibration flag
        if os.path.exists(CALIBRATION_FLAG):
            with open(CALIBRATION_FLAG, 'r') as calib:
                try:
                    if "ON" in calib.read():
                        self.defaults["calibrate"] = True
                except Exception as e:
                    log_error("Something happened trying to read the calibration flag for the webcam. Ignoring it.", e)

        log(f"Calibration data collection is {'ON' if self.defaults['calibrate'] else 'OFF'}")

        # Check if the calibration parameters are overridden
        self.a_value = LUM_SPEED_PARAM_A
        self.b_value = LUM_SPEED_PARAM_B

        if os.path.exists(CALIBRATED_PARAMS):
            with open(CALIBRATED_PARAMS, 'r') as calib:
                try:
                    self.a_value, self.b_value = [int(v) for v in calib.readlines()[0].split(",")]
                except Exception as e:
                    log_error("Something happened trying to read the overridden calibration parameters for the webcam. Ignoring them.", e)
        
        log(f"Camera configuration for low light: A={self.a_value}, B={self.b_value}")
        

    def __getattr__(self, name):
        """ 
        Provide some fallback value for all the expected fields of 'image'.
        Logs the access to highlight values that are not set, but were used.
        """
        value = self.defaults.get(name, None)
        #log(f"WARNING: Accessing default value for {name}: {value}")
        return value
        

    def take_picture(self) -> None:
        """
        Takes the picture and renders the elements on it.
        """
        # NOTE: let exceptions here escalate. Do not catch or at least rethrow!
        self.shoot_picture()
        self.process_picture()
            

    def shoot_picture(self) -> None:
        """
        Shoots the picture using PiCamera.
        If the luminance is found to be too low, adjusts the shutter speed camera value and tries again.
        """
        self._shoot_picture()
        
        # Test the luminance: if the picture is bright enough, return
        photo = Image.open(str(self.temp_photo_path))
        luminance = self.luminance_from_picture(photo)
        if luminance >= MINIMUM_DAYLIGHT_LUMINANCE:
            return

        # We're in low light conditions.
        log(f"Low light detected: {luminance:.2f} (min is {MINIMUM_DAYLIGHT_LUMINANCE}).")

        if not self.calibrate:
            # Calculate new shutter speed and retry
            shutter_speed = self.shutter_speed_from_picture(photo)
            log(f"Shooting again with exposure time set to {shutter_speed/10**6:.2f}s. "
                f"Expected final luminance: {self.compute_target_luminance(luminance):.2f}.")
            self._shoot_picture(shutter_speed=shutter_speed)

        else:
            # We're in low light conditions and we're recalibrating the camera.
            # Do a binary search over the shutter speed space, within 0.03s and 3s
            # Might require several attempts, but is bound to max 20 (see exit conditions)
            min_speed = MIN_SHUTTER_SPEED
            max_speed = MAX_SHUTTER_SPEED
            luminosity_margin = TARGET_LUMINOSITY_MARGIN
            target_luminance = self.compute_target_luminance(luminance)
            log(f"Entering calibration procedure. "
                f"Parameters: min shutter speed = {MIN_SHUTTER_SPEED}, "
                f"max shutter speed = {MAX_SHUTTER_SPEED}, "
                f"target luminance = {target_luminance}")

            i = 0
            while True:
                
                # Update shutter speed and read resulting luminosity
                i += 1
                shutter_speed = int((min_speed + max_speed) / 2)
                self._shoot_picture(shutter_speed=shutter_speed)
                new_luminance = self.luminance_from_picture(Image.open(str(self.temp_photo_path)))
                
                if new_luminance >= target_luminance - TARGET_LUMINOSITY_MARGIN and \
                   new_luminance <= target_luminance + TARGET_LUMINOSITY_MARGIN:
                    log(f"Tentative {i}: successful! Initial luminance: {luminance:.2f}, final luminance: {new_luminance:.2f}, shutter speed: {shutter_speed}")
                    
                    with open(CALIBRATION_DATASET, 'a') as table:
                        table.write(f"{luminance:.2f}\t{new_luminance:.2f}\t{shutter_speed}\n")
                    break

                if new_luminance < target_luminance - TARGET_LUMINOSITY_MARGIN:
                    log(f"Tentative {i}: too dark. Luminance: {new_luminance:.2f}, speed: {shutter_speed/10**6:.2f}. Increasing!")
                    min_speed = shutter_speed

                else:
                    log(f"Tentative {i}: too bright. Luminance: {new_luminance:.2f}, speed: {shutter_speed/10**6:.2f}. Decreasing!")
                    max_speed = shutter_speed

                # Exit condition - 20 iterations with the default max/min speeds
                if min_speed + 5 > max_speed:
                    log(f"Search failed! Using the last value ({shutter_speed}, resulting luminance: {new_luminance}) and exiting the calibration procedure.")
                    break


    def _shoot_picture(self, shutter_speed: Optional[int] = None) -> None:
        """ 
        Actually shoots the picture using PiCamera.
        shutter_speed is useful for evening and night picture, and setting it triggers the evening mode.
        """
        log("Adjusting camera...")

        with PiCamera(framerate=(Fraction(1, 10), Fraction(5, 1))) as camera:

            if int(self.width) > camera.MAX_RESOLUTION.width:
                log(f"WARNING! The requested image width ({self.width}) "
                    f"exceeds the maximum width resolution for this camera ({camera.MAX_RESOLUTION.width}). "
                    "Using the maximum width resolution instead.")
                self.width = camera.MAX_RESOLUTION.width

            if int(self.height) > camera.MAX_RESOLUTION.height:
                log(f"WARNING! The requested image height ({self.height}) "
                    f"exceeds the maximum height resolution for this camera ({camera.MAX_RESOLUTION.height}). "
                    "Using the maximum height resolution instead.")
                self.height = camera.MAX_RESOLUTION.height

            camera.resolution = (int(self.width), int(self.height))
            camera.vflip = self.ver_flip
            camera.hflip = self.hor_flip
            camera.rotation = int(self.rotation)
            camera.awb_mode = "sunlight"
            camera.meter_mode = "matrix"

            # Give the camera firmwaresome time to adjust
            if shutter_speed:
                camera.shutter_speed = shutter_speed
                camera.iso = 800
                sleep(4)
                camera.exposure_mode = "off"
                log("Taking low light picture")
            else:
                sleep(4)
                log("Taking picture")

            camera.capture(str(self.temp_photo_path))

            photo = Image.open(str(self.temp_photo_path))
            luminance = self.luminance_from_picture(photo)
            log(f"Picture taken. Luminance: {luminance:.2f}, exposure speed: {camera.exposure_speed}, shutter speed: {camera.shutter_speed}")


    def shutter_speed_from_picture(self, photo):
        """
        Given a picture with low luminosity (< MINIMUM_DAYLIGHT_LUMINANCE)
        returns the appropriate shutter speed to acheve a good target luminosity
        """
        return self.shutter_speed_from_luminance(self.luminance_from_picture(photo))


    def shutter_speed_from_luminance(self, luminance):
        """
        Given a low luminance value, return the shutter speed required to raise the 
        final luminance to the expected target luminance
        """
        if luminance < MINIMUM_DAYLIGHT_LUMINANCE:
            return int(((self.a_value / luminance) + self.b_value))
        return None

    @staticmethod
    def luminance_from_picture(photo):
        """
        Given a PIL picture, returns its luminance
        """
        return Camera.luminance_from_rgb(*ImageStat.Stat(photo).mean)

    @staticmethod
    def luminance_from_rgb(r, g, b):
        """
        Given the RGB values of a picture (ImageStat.Stat(photo).mean)
        returns its luminance
        """
        return math.sqrt(0.241*(r**2) + 0.691*(g**2) + 0.068*(b**2))

    @staticmethod
    def compute_target_luminance(luminance):
        """
        Given a luminance < MINIMUM_DAYLIGHT_LUMINANCE, 
        calculate an appropriate luminance value to raise the image to
        """
        if luminance > MINIMUM_DAYLIGHT_LUMINANCE:
            return luminance 
        if luminance < 30:
            return luminance+30 
        else:
            return (luminance/2) + 45


    def process_picture(self) -> None:
        """ 
        Renders text and images over the picture and saves the resulting image.
        """
        log("Processing picture")

        # Open and measures the picture
        try:
            photo = Image.open(self.temp_photo_path).convert("RGBA")
        except Exception as e:
            log_error("Failed to open the image for editing. "
                      "The photo will have no overlays applied.", e)
            return

        # Create the overlay images
        rendered_overlays = []
        for position, data in self.overlays.items():
            try:
                overlay = Overlay(position, data, photo.width, photo.height, self.date_format, self.time_format)
                if overlay.rendered_image:
                    rendered_overlays.append(overlay)
                    
            except Exception as e:
                log_error(f"Something happened processing the overlay {position}. "
                "This overlay will be skipped.", e)
        
        # Calculate final image size
        border_top = 0
        border_bottom = 0
        for overlay in rendered_overlays:                        
            # If this overlay is out of the picture, add its height to the 
            # final image size (above or below)
            if not overlay.over_the_picture:
                if overlay.vertical_position == "top":
                    border_top = max(border_top, overlay.rendered_image.height)
                else:
                    border_bottom = max(border_bottom, overlay.rendered_image.height)
        total_height = photo.height + border_top + border_bottom

        # Generate canvas of the correct size
        image = Image.new("RGBA", 
                          (photo.width, total_height),
                          color=self.background_color)

        # Add the picture on the canvas
        image.paste(photo, (0, border_top))

        # Add the overlays on the canvas in the right position
        for overlay in rendered_overlays:
            if overlay.rendered_image:  # it might be None if it failed along the way
                x, y = overlay.compute_position(image.width, image.height, border_top, border_bottom)
                image.paste(overlay.rendered_image, (x, y), mask=overlay.rendered_image)  # mask is to allow for transparent images
        
        # Save the image appropriately
        if self.extension.lower() in ["jpg", "jpeg"]:
            image = image.convert('RGB')
            image.save(DATA_PATH / self.processed_image_path, format='JPEG', 
                subsampling=self.jpeg_subsampling, quality=self.jpeg_quality)
        else:
            image.save(DATA_PATH / self.processed_image_path)
