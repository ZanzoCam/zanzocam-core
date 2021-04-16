from typing import Any, Dict, Tuple, Optional

import os
import math
import piexif
import datetime
import textwrap
from time import sleep
from pathlib import Path
from picamera import PiCamera
from fractions import Fraction
from PIL import Image, ImageFont, ImageDraw, ImageStat

from constants import *
from webcam.utils import log, log_error
from webcam.system import System
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

        # TEMPORARY STUFF< HANDLE BETTER!
        self.use_low_light_algorithm = True
        self.let_awb_settle_in_dark = True


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


    def _prepare_camera_object(self, expanded_framerate_range: bool = False) -> int:
        """ 
        Sets up the camera object in a consistent way. Returns the PiCamera object, ready to use.
        if `expanded_framerate_range` is given, framerate_range is set to (1/10, 90).
        Use this function in `with` blocks only, or remember to close the returned `camera` object!
        """
         # NOTE: let exceptions here escalate. Do not catch or at least rethrow!
        if expanded_framerate_range:
            camera = PiCamera(framerate_range=(Fraction(1, 10), Fraction(90, 1)))
        else:
            camera = PiCamera()

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

    def _camera_capture(self, camera):
        """
        Takes a picture and saves it in the temporary picture path,
        taking care of the logging too.
        """
        log("Taking picture...")
        camera.capture(str(self.temp_photo_path))
        log(f"Picture taken (exposure speed: {camera.exposure_speed/10**6:.4f}, "
            f"shutter speed: {camera.shutter_speed/10**6:.4f}, iso: {camera.iso})")
            

    def shoot_picture(self) -> None:
        """
        Shoots the picture using PiCamera. If the luminance is found  
        to be too low, uses an iterative algorithm to adjusts the 
        shutter speed of the camera value and tries again.
        """
         # NOTE: let exceptions here escalate. Do not catch or at least rethrow!

        with self._prepare_camera_object() as camera:
            log(f"Camera warm-up ({CAMERA_WARM_UP_TIME}s)...")
            sleep(CAMERA_WARM_UP_TIME)
            self._camera_capture(camera)

        # If the low light algorithm is disabled, return
        if not self.use_low_light_algorithm:
            log(f"Luminance won't be checked, because `use_low_light_algorithm = False`")
            return

        # Test the luminance: if the picture is bright enough, return
        initial_luminance = self.luminance_from_path(self.temp_photo_path)
        if initial_luminance >= MINIMUM_DAYLIGHT_LUMINANCE:
            log(f"Daylight luminance detected: {initial_luminance:.2f} "
                f"(lower bound is {MINIMUM_DAYLIGHT_LUMINANCE})")
            return

        # We're in low light conditions and allowed to try correcting it.
        # Calculate new shutter speed with the low light algorithm
        new_luminance, shutter_speed, iso, attempts = self.low_light_search(initial_luminance)

        # If we're good without one final picture with the long wait for the AWB, return here
        if not self.let_awb_settle_in_dark:
            log(f"No more pictures will be taken, because `let_awb_settle_in_dark = False`")
            return

        # Once the correct shutter speed has been found, shoot again a picture with the correct params.
        log(f"Taking one more picture with the final parameters "
            f"(shutter speed: {shutter_speed/10**6:.2f}s, ISO: {iso})")

        with self._prepare_camera_object(expanded_framerate_range=True) as camera:
            camera.shutter_speed = shutter_speed
            camera.iso = iso
            
            timeout = (shutter_speed/10**6) * 7 + 5
            log(f"Adjusting white balance: will take {timeout:.1f} seconds...")
            sleep(timeout)
            camera.exposure_mode = "off"

            self._camera_capture(camera)

        final_luminance = self.luminance_from_path(str(self.temp_photo_path))
        log(f"Final luminance: {final_luminance:.2f}.")


    def low_light_search(self, initial_luminance: int) -> Tuple[float, int, int, int]:
        """
        Tries to find the correct shutter speed in low-light conditions.
        Returns the final luminance, the shutter speed, and the number of attempts done, in this order.
        """
        target_luminance = self.compute_target_luminance(initial_luminance)        
        log(f"Low light detected: {initial_luminance:.2f} (lower bound is {MINIMUM_DAYLIGHT_LUMINANCE})")
        log(f"Trying to get a brighter image. "
            f"Target luminance: {target_luminance:.2f} (tolerance: {TARGET_LUMINOSITY_MARGIN}), "
            f"max exposure time: {MAX_SHUTTER_SPEED/10**6:.2f}, initial ISO: {INITIAL_LOW_LIGHT_ISO}")

        # When luminance is <1, the equation doesn't work very well and 
        # gives an overestimated shutter speed value. So we'd rather
        # attempt a random 2sec shot to get a better initial estimate
        # of the actual ambient luminance and try again
        if initial_luminance < 1:
            log(f"Luminance is below {NO_LUMINANCE_THRESHOLD}: shutter speed set to {NO_LUMINANCE_SHUTTER_SPEED/10**6:.2f}s")
            shutter_speed = NO_LUMINANCE_SHUTTER_SPEED
        else:
            shutter_speed = MIN_SHUTTER_SPEED
    
        new_luminance = initial_luminance

        # Note that we're looping within this block for a reason!
        # Re-initializing the camera for every picture would take a lot of
        # time and require a warm-up of at least 5 seconds every time.
        with self._prepare_camera_object(expanded_framerate_range=True) as camera:

            camera.iso = INITIAL_LOW_LIGHT_ISO
            log(f"Camera warm-up ({CAMERA_WARM_UP_TIME}s)...")
            sleep(CAMERA_WARM_UP_TIME)

            for attempt in range(1, 10):

                # Take the picture & check the luminance
                #camera.framerate = (10**6) / (shutter_speed)
                camera.shutter_speed = shutter_speed          
                camera.exposure_mode = "off"
                self._camera_capture(camera)
                new_luminance = self.luminance_from_path(self.temp_photo_path)

                # In rare cases, the camera might return pitch black images for no good reason.
                # So if the luminance is 0, just retry.
                if new_luminance <= 0.001:  # Should not be needed, but with floats you never know
                    pass
                
                # Too bright: log and retry without further checks
                elif new_luminance > (target_luminance + TARGET_LUMINOSITY_MARGIN):
                    log(f"# {attempt}: bright. Luminance achieved: {new_luminance:.2f}. Down!")
                
                # Too dark: log and check if you can proceed, raising ISO if so required
                elif new_luminance < (target_luminance - TARGET_LUMINOSITY_MARGIN):
                    log(f"# {attempt}: dark. Luminance achieved: {new_luminance:.2f}. Up!")
                    
                    # If the max shutter speed and max ISO is already reached, break: 
                    # you can't reach the target luminance
                    if shutter_speed == MAX_SHUTTER_SPEED:
                        if camera.iso == 800:
                            log_error(f"ISO is at 800 and shutter speed is at max ({MAX_SHUTTER_SPEED/10**6:.2f}). Cannot proceed")
                            return new_luminance, shutter_speed, camera.iso, attempt

                        log(f"Not allowed to raise the shutter speed further. "
                            f"Increasing ISO from {camera.iso} to {camera.iso*2} and trying again")
                        camera.iso = camera.iso*2

                # Otherwise return the match
                else:
                    log(f"# {attempt}: OK! Luminance achieved: {new_luminance:.2f}")
                    return new_luminance, shutter_speed, camera.iso, attempt

                # Compute the shutter speed and loop
                shutter_speed = self.low_light_equation(shutter_speed, new_luminance, target_luminance)

            # Exit condition - 10 iterations      
            log_error(f"The low light algorithm failed! "
                      f"Returning the last values (shutter speed: {shutter_speed}, luminance: {new_luminance}, iso: {camera.iso})")
            return new_luminance, shutter_speed, camera.iso, attempt
        
    @staticmethod
    def low_light_equation(shutter_speed, initial_luminance, target_luminance) -> int:
        """
        Given a starting luminance, computes the best estimate of 
        the shutter speed needed to achieve the target luminance.
        """
        target_shutter_speed = (shutter_speed / initial_luminance) * target_luminance

        if target_shutter_speed > MAX_SHUTTER_SPEED:
            log(f"Max shutter speed has been reached, capping it to {MAX_SHUTTER_SPEED/10**6}")
            return int(MAX_SHUTTER_SPEED)

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
                      "The photo will have no overlays applied", e)
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
                "This overlay will be skipped", e)
        
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
        
        # Recover the EXIF data
        exif_dict = piexif.load(photo.info["exif"])
        version = System.get_version()
        exif_dict["0th"][piexif.ImageIFD.Make] = f"ZANZOCAM {version}"
        exif_dict["0th"][piexif.ImageIFD.Software] = f"ZANZOCAM {version}"
        exif_dict["0th"][piexif.ImageIFD.ProcessingSoftware] = f"ZANZOCAM {version}"
        exif_bytes = piexif.dump(exif_dict)

        # Save the image appropriately
        if self.extension.lower() in ["jpg", "jpeg"]:
            image = image.convert('RGB')
            image.save(DATA_PATH / self.processed_image_path, format='JPEG', 
                subsampling=self.jpeg_subsampling, quality=self.jpeg_quality,
                exif=exif_bytes)
        else:
            image.save(DATA_PATH / self.processed_image_path, exif=exif_bytes)
