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



class Camera:
    """
    Manages the pictures taking process.
    """
    def __init__(self, configuration: Configuration):
        log("Initializing camera")

        # Provide defaults for all the expected values of 'image'
        self.defaults = CAMERA_DEFAULTS
        
        # Populate the attributes with the 'image' data 
        if "image" not in vars(configuration).keys():
            log("WARNING! No image information present in the configuration! "
                "Please fix the error ASAP. Fallback values are being used.")
            configuration.image = CAMERA_DEFAULTS
        
        for key, value in configuration.image.items():
            setattr(self, key, value)

        # There might be no overlays
        self.overlays = getattr(configuration, 'overlays', {})
        
        # Image name
        self.temp_photo_path = DATA_PATH / ('.temp_image.' + self.extension)
        self.processed_image_path = DATA_PATH / ('.final_image.' + self.extension)

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
        return self.defaults.get(name, None)
        

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
        initial_luminance = self._shoot_picture()
        
        # Test the luminance: if the picture is bright enough, return
        if initial_luminance >= MINIMUM_DAYLIGHT_LUMINANCE:
            return

        # We're in low light conditions.
        # Calculate new shutter speed and retry
        shutter_speed = self.shutter_speed_from_luminance(initial_luminance)
        log(f"Low light detected: {initial_luminance:.2f} (min is {MINIMUM_DAYLIGHT_LUMINANCE}). "
            f"Expected luminance: {self.compute_target_luminance(initial_luminance):.2f}.")
        self._shoot_picture(shutter_speed=shutter_speed)


    def _shoot_picture(self, shutter_speed: Optional[int] = None) -> int:
        """ 
        Actually shoots the picture using PiCamera.
        shutter_speed is useful for evening and night picture, and setting it triggers the evening mode.
        Returns the image luminance.
        """
        if shutter_speed:
            log(f"Shooting with exposure time set to {shutter_speed/10**6:.2f}s.")

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
            camera.meter_mode = "matrix"

            # Give the camera firmwaresome time to adjust
            if shutter_speed:
                camera.shutter_speed = shutter_speed
                camera.iso = 800
                sleep(10)  # More time allows for a better white balancing. Some suggest even 30s!
                camera.exposure_mode = "off"
                log("Taking low light picture")
            else:
                sleep(4)
                log("Taking picture")

            camera.capture(str(self.temp_photo_path))

            luminance = self.luminance_from_path(self.temp_photo_path)
            log(f"Picture taken. Luminance: {luminance:.2f}, exposure speed: {camera.exposure_speed}, shutter speed: {camera.shutter_speed}")
            return luminance


    def gather_calibration_data(self):
        """
        Data gathering procedure. Each time it's called, takes a finite amount
        of pictures and measures the luminance. Then saves the sample data into
        the samples dataset in the format: initial_luminance,actual_luminance,speed
        """
        log(f"Entering data gathering procedure. Parameters: "
            f"min shutter speed = {MIN_SHUTTER_SPEED/(10**6):.2f}s, "
            f"max shutter speed = {MAX_SHUTTER_SPEED/(10**6):.2f}s, "
            f"multiplication factor = {MULT_SHUTTER_SPEED}.")

        # Get the initial luminance
        log("Taking reference picture.")
        self._shoot_picture()
        initial_luminance = self.luminance_from_path(self.temp_photo_path)
        log(f"Initial luminance with no shutter speed set: {initial_luminance:.2f}")

        speed = MIN_SHUTTER_SPEED
        while speed < MAX_SHUTTER_SPEED:         
            
            # Take a picture with this shutter speed
            speed *= MULT_SHUTTER_SPEED
            self._shoot_picture(shutter_speed=int(speed))
            actual_luminance = self.luminance_from_path(self.temp_photo_path)
            log(f"Sample speed={speed/(10**6):.2f}s: luminance={actual_luminance:.2f}")

            # Save the data into the dataset
            with open(CALIBRATION_DATASET, 'a') as table:
                table.write(f"{initial_luminance:.2f},{actual_luminance:.2f},{int(speed)}\n")

        log("Data gathering complete.")


    def shutter_speed_from_path(self, path: Path) -> int:
        """
        Given a path to a picture with low luminosity (< MINIMUM_DAYLIGHT_LUMINANCE)
        returns the appropriate shutter speed to acheve a good target luminosity
        """
        return self.shutter_speed_from_luminance(self.luminance_from_path(path))


    def shutter_speed_from_luminance(self, luminance: int) -> int:
        """
        Given a low luminosity value (< MINIMUM_DAYLIGHT_LUMINANCE)
        returns the appropriate shutter speed to acheve a good target luminosity
        """
        if luminance < MINIMUM_DAYLIGHT_LUMINANCE:
            return int(((self.a_value / luminance) + self.b_value))
        return None

    @staticmethod
    def luminance_from_path(path: Path) -> int:
        """
        Given a path to an image, returns its luminance
        """
        photo = Image.open(str(path))
        r, g, b = ImageStat.Stat(photo).mean
        return math.sqrt(0.241*(r**2) + 0.691*(g**2) + 0.068*(b**2))


    @staticmethod
    def compute_target_luminance(luminance: int) -> int:
        """
        Given a luminance < MINIMUM_DAYLIGHT_LUMINANCE, 
        calculate an appropriate luminance value to raise the image to
        """
        if luminance > MINIMUM_DAYLIGHT_LUMINANCE:
            return luminance 
        if luminance < MINIMUM_NIGHT_LUMINANCE:
            return luminance + (MINIMUM_NIGHT_LUMINANCE) 
        else:
            return (luminance/2) + MINIMUM_NIGHT_LUMINANCE*1.5


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
