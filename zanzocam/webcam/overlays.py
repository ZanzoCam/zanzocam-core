from typing import Any, Dict, Tuple, Optional

import os
import math
import datetime
import textwrap
from pathlib import Path
from PIL import Image, ImageFont, ImageDraw

from constants import *
from webcam.utils import log, log_error



class Overlay:
    """
    Represents one overlay to add to the picture.
    """
    def __init__(self, position: str, data: Dict, photo_width: int, photo_height: int, date_format: Optional[str], time_format: Optional[str]):
        log(f"Creating overlay {position}.")
        
        # Where the rendered overlay is stored if can be generated
        self.rendered_image = None
        self.defaults = {
            "font_size": 25,
            "padding_ratio": 0.2,
            "text": "~~~ DEFAULT TEXT ~~~",
            "font_color": (0, 0, 0),
            "background_color": (255, 255, 255, 0),
            "image": "fallback-pixel.png",
            "width": None,   # Might be unset to retain aspect ratio
            "heigth": None,  # Might be unset to retain aspect ratio
            "over_the_picture": False,
        }
        
        # Populate the attributes with the overlay data 
        for key, value in data.items():
            setattr(self, key, value)
        self.date_format = date_format if date_format else "%d %B %Y"
        self.time_format = time_format if time_format else "%H:%M"

        # Store position information
        try:
            self.vertical_position, self.horizontal_position = position.lower().split("_")
            if ((self.vertical_position != "top" and 
                 self.vertical_position != "bottom") or
                (self.horizontal_position != "left" and 
                 self.horizontal_position != "center" and 
                 self.horizontal_position != "right")):
                raise ValueError()
 
        except Exception as e:
            log_error(f"The position of this overlay ({position}) is malformed. "
                "It must be one of the following: top_left, top_center, "
                "top_right, bottom_left, bottom_center, bottom_right."
                "This overlay will be skipped.", e)
            return
            
        # Find the type of overlay
        if not data.get("type", None) or not isinstance(data.get("type"), str):
            log(f"Overlay type not specified for position "
                f"{position}. This overlay will be skipped.")
            return
        self.type = data.get("type")

        if self.type == "text":
            self.rendered_image = self.create_text_overlay(photo_width, photo_height)

        elif self.type == "image":
            self.rendered_image = self.create_image_overlay()
        
        else:
            log_error(f"Overlay type '{self.type}' not recognized. Valid names: "
            "text, image. This overlay will be skipped.")
            return


    def __getattr__(self, name):
        """ 
        Provide some fallback value for all the expected fields of 'overlay'.
        Logs the access to highlight values that are not set, but were used.
        """
        if name in self.defaults.keys():
            #log(f"WARNING: Accessing default value for {name}: {value}")
            return self.defaults[name]
        return None


    def compute_position(self, image_width: int, image_height: int, 
                border_top: int, border_bottom: int) -> Tuple[int, int]:
        """
        Returns the x,y position in the picture where this overlay 
        should be pasted.
        """
        x, y = 0, 0
        
        if self.horizontal_position == "left":
            x = 0
            
        elif self.horizontal_position == "right":
            x = image_width - self.rendered_image.width
            
        elif self.horizontal_position == "center":
            x = int((image_width - self.rendered_image.width)/2)

        if self.vertical_position == "top":
            if self.over_the_picture:
                y = border_top
            else:
                y = 0
                
        elif self.vertical_position == "bottom":
            if self.over_the_picture:
                y = image_height - self.rendered_image.height - border_bottom
            else:
                y = image_height - self.rendered_image.height
                
        return x, y


    def create_text_overlay(self, photo_width: int, photo_height: int) -> Any:
        """ 
        Prepares an overlay containing text.
        In case of issues, self.overlay_image will stay None.
        """
        try:
            # Creates the font and calculate the line height
            font_size = self.font_size
            font = ImageFont.truetype(FONT_PATH, font_size)
            line_height = font.getsize("a")[1] * 1.5

            # Calculate the padding as a percentage of the line height
            padding_ratio = self.padding_ratio
            padding = math.ceil(line_height*padding_ratio)

            # Replace %%TIME and %%DATE with respective values
            time_string = datetime.datetime.now().strftime(self.time_format)
            date_string = datetime.datetime.now().strftime(self.date_format)
            self.text = self.text.replace("%%TIME", time_string)
            self.text = self.text.replace("%%DATE", date_string)

            # Calculate the dimension of the text with the padding added
            text_width, text_height = self.process_text(font, photo_width)
            text_size = (text_width + padding*2, text_height + padding*2)

            # Some very popular browsers use \r\n to save newlines from 
            # textareas: normalize
            self.text = self.text.replace("\r\n", "\n")

            # Creates the image
            label = Image.new("RGBA", text_size, color=self.background_color)
            draw = ImageDraw.Draw(label)
            draw.text((padding, padding, padding), self.text, self.font_color, font=font)

            # Store it
            return label

        except Exception as e:
            log_error("Something unexpected happened while generating text the overlay. "+
            "This overlay will be skipped", e)
            return


    def process_text(self, font: Any, max_line_length: int) -> Tuple[int, int]:
        """ 
        Measures and insert returns into the text to make it fit into the image.
        """
        # Insert as many returns as needed to make the text fit.
        lines = []
        for line in self.text.split("\n"):
            if font.getsize(line)[0] <= max_line_length:
                lines.append(line)
            else:
                new_line = ""
                for word in line.split(" "):
                    if font.getsize(new_line + word)[0] <= max_line_length:
                        new_line = new_line + word + " "
                    else:
                        lines.append(new_line)
                        new_line = word + " "
                if new_line != "":
                    lines.append(new_line)
        self.text = '\n'.join(lines)

        # Create a temporary image to measure the text size
        temp = Image.new("RGBA", (1,1))
        temp_draw = ImageDraw.Draw(temp)
        return temp_draw.textsize(self.text, font)


    def create_image_overlay(self) -> Any:
        """ 
        Prepares an overlay containing an image.
        Might return None in case of issues. 
        """
        overlay_image_path = IMAGE_OVERLAYS_PATH / self.path

        try:
            image = Image.open(overlay_image_path).convert("RGBA")
        except Exception as e:
            log_error(f"Image '{overlay_image_path}' can't be found or is "
            "impossible to open. This overlay will be skipped", e)
            return

        try:
            # Calculate new dimension, retaining aspect ratio if necessary
            if self.width and not self.height:
                aspect_ratio = image.width / image.height
                self.height = math.ceil(self.width / aspect_ratio)

            if not self.width and self.height:
                aspect_ratio = image.height / image.width
                self.width = math.ceil(self.height / aspect_ratio)

            # Do not resize if no size is given
            if self.width and self.height:
                image = image.resize((self.width, self.height))

            padding_width = math.ceil(image.width*self.padding_ratio)
            padding_height = math.ceil(image.height*self.padding_ratio)

            overlay_size = (image.width+padding_width*2, image.height+padding_height*2)
            overlay = Image.new("RGBA", overlay_size, color=self.background_color)
            overlay.paste(image, (padding_width, padding_height), mask=image)

            return overlay
            
        except Exception as e:
            log_error("Something unexpected happened while generating "
                      "the image overlay. This overlay will be skipped", e)
            return
