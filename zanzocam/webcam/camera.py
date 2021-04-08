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


from time import time
ISO = 400
MIN_SHUTTER_SPEED = int(0.03 * 10**6)
MAX_SHUTTER_SPEED = int(9.5 * 10**6)
TARGET_LUMINOSITY_MARGIN = 3
CAMERA_WARM_UP_TIME = 5


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


    def _prepare_camera_object(self, shutter_speed: Optional[int] = None) -> int:
        """ 
        Sets up the camera object in a consistent way. 
        Returns the PiCamera object, ready to use
        Use this function in with blocks only, or remember to close the camera object!
        """
         # NOTE: let exceptions here escalate. Do not catch or at least rethrow!

        log("Setting up camera...")
        camera = PiCamera(framerate_range=(Fraction(1, 10), Fraction(5, 1)))

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
        return camera
            

    def shoot_picture(self) -> None:
        """
        Shoots the picture using PiCamera.
        If the luminance is found to be too low, adjusts the shutter speed camera value and tries again.
        """
         # NOTE: let exceptions here escalate. Do not catch or at least rethrow!

        with self._prepare_camera_object() as camera:
            log(f"Camera warm-up ({CAMERA_WARM_UP_TIME}s)...")
            sleep(CAMERA_WARM_UP_TIME)
            log("Taking picture...")
            camera.capture(str(self.temp_photo_path))
            log(f"Picture taken. Exposure speed: {camera.exposure_speed/10**6:.4f}, "
                f"shutter speed: {camera.shutter_speed/10**6:.4f}")

        initial_luminance = self.luminance_from_path(self.temp_photo_path)
        # Test the luminance: if the picture is bright enough, return
        if initial_luminance >= MINIMUM_DAYLIGHT_LUMINANCE:
            log(f"Daylight luminance detected: {initial_luminance:.2f} "
                f"(min is {MINIMUM_DAYLIGHT_LUMINANCE}).")
            return

        # We're in low light conditions.
        # Calculate new shutter speed with the low light algorithm and retry
        luminosity_margin = TARGET_LUMINOSITY_MARGIN
        target_luminance = self.compute_target_luminance(initial_luminance)
        
        log(f"Low light detected: {initial_luminance:.2f} (min is {MINIMUM_DAYLIGHT_LUMINANCE}).")
        log(f"Target luminance: {target_luminance:.2f} (tolerance: {TARGET_LUMINOSITY_MARGIN}).")

        start_time = time()  # FIXME Remove later, redundant
        log(f"Low light parameters: max shutter speed: {MAX_SHUTTER_SPEED}, initial ISO: {ISO}, "
            f"target luminance: {target_luminance:.2f}, luminance tolerance: {TARGET_LUMINOSITY_MARGIN}")
        

        new_luminance, shutter_speed, attempts = self.low_light_search(target_luminance)
        

        # FIXME remove me before release, this is a redundant step
        # Once the correct shutter speed has been found, shoot again a picture with the correct params.
        log("Take one more picture with the correct parameters")
        with self._prepare_camera_object() as camera:
            camera.shutter_speed = shutter_speed
            camera.iso = ISO
            
            timeout = (shutter_speed/10**6) * 7 + 5
            log(f"Adjusting white balance: will take {timeout:.1f} seconds...")
            sleep(timeout)
            camera.exposure_mode = "off"
            
            log(f"Taking picture with shutter speed set to {shutter_speed/10**6:.4f}s.")
            camera.capture(str(self.temp_photo_path))
            log(f"Picture taken: exposure speed: {camera.exposure_speed/10**6:.4f}, shutter speed: {camera.shutter_speed/10**6:.4f}")

        final_luminance = self.luminance_from_path(str(self.temp_photo_path))
        log(f"The final luminance is {final_luminance:.2f}, with shutter speed: {shutter_speed}.")

        # Save data
        execution_time = time() - start_time
        with open("low_light_data", 'a') as table:
            table.write(f"{initial_luminance:.2f}\t\t{new_luminance:.2f}\t\t{final_luminance:.2f}\t\t"
                        f"{shutter_speed/10**6:.2f}\t\t{ISO}\t\t{execution_time:.2f}\t\t{attempts}\n")


    def low_light_search(self, target_luminance: int) -> Tuple[float, int, int]:
        """
        Tries to find the correct shutter speed in low-light conditions.
        Returns the final luminance, the shutter speed, and the number of attempts done, in this order.
        """
        initial_luminance = self.luminance_from_path(str(self.temp_photo_path))
        shutter_speed = self.low_light_equation(MIN_SHUTTER_SPEED, initial_luminance, target_luminance)
        new_luminance = initial_luminance

        with self._prepare_camera_object() as camera:
            camera.iso = ISO
            log(f"Camera warm-up ({CAMERA_WARM_UP_TIME}s)...")
            sleep(CAMERA_WARM_UP_TIME)

            for attempt in range(1, 20):
                # When luminance is <1, the Paolo equation doesn't work very well and 
                # gives an overestimated shutter speed value, causing time loss
                if attempt == 1 and new_luminance < 1:
                    log("Shutter speed set to 2s")
                    shutter_speed  = 2 * 10**6

                camera.framerate = (10**6) / (shutter_speed)
                camera.shutter_speed = shutter_speed          
                log("Taking picture")
                camera.exposure_mode = "off"
                camera.capture(str(self.temp_photo_path))

                # Read resulting luminosity and update shutter speed if necessary
                new_luminance = self.luminance_from_path(self.temp_photo_path)
                
                if new_luminance >= (target_luminance - TARGET_LUMINOSITY_MARGIN) and \
                    new_luminance <= (target_luminance + TARGET_LUMINOSITY_MARGIN):
                    log(f"Tentative {attempt}: successful! Initial luminance: {initial_luminance:.2f}, "
                        f"final luminance: {new_luminance:.2f}, shutter speed: {shutter_speed}")
                    return new_luminance, shutter_speed, attempt

                if new_luminance < (target_luminance - TARGET_LUMINOSITY_MARGIN):
                    log(f"Tentative {attempt}: too dark. "
                        f"Luminance: {new_luminance:.2f}, speed: {shutter_speed/10**6:.2f}. Increasing!")
                    
                    # If the maximun shutter speed is already reached, break: you can't reach the target luminance
                    if shutter_speed == MAX_SHUTTER_SPEED:
                        if camera.iso == 800:
                            log(f"ISO is at 800 and shutter speed is at max ({MAX_SHUTTER_SPEED/10**6:.2f}). Cannot proceed.")
                            return new_luminance, shutter_speed, attempt

                        log(f"Not allowed to go above {shutter_speed/10**6}s. Increasing ISO from {ISO} to 800 and trying again.")
                        camera.iso = 800
                        
                    shutter_speed = self.low_light_equation(shutter_speed, new_luminance, target_luminance)

                else:
                    log(f"Tentative {attempt}: too bright. Luminance: {new_luminance:.2f}, speed: {shutter_speed/10**6:.2f}. Decreasing!")
                    shutter_speed = self.low_light_equation(shutter_speed, new_luminance, target_luminance)

            # Exit condition - 20 iterations with the default max/min speeds            
            log(f"Search failed! Using the last value ({shutter_speed}, "
                f"resulting luminance: {new_luminance}) and exiting the binary search procedure.")
            return new_luminance, shutter_speed, attempt
        

    def low_light_equation(self, shutter_speed, initial_luminance, target_luminance) -> int:
        target_shutter_speed = (shutter_speed / initial_luminance) * target_luminance
        if target_shutter_speed > MAX_SHUTTER_SPEED:
            target_shutter_speed = MAX_SHUTTER_SPEED
            log(f"Max shutter speed {target_shutter_speed/10**6} has been reached, using {MAX_SHUTTER_SPEED/10**6}")
        return int(target_shutter_speed)


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
