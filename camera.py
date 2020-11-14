#!/usr/bin/python3

import math
import json
import datetime
import textwrap
from picamera import PiCamera
from PIL import Image, ImageFont, ImageDraw

    
def shoot_picture():
    """ Scatta la foto """
    camera = PiCamera()
    camera.vflip = True
    image_name = '.temp_image.jpg'
    camera.capture(image_name)
    return image_name
    
    

def _process_text(font, user_text, max_line_length):
    text = '\n'.join(['\n'.join(textwrap.wrap(line, max_line_length,
                     break_long_words=False, replace_whitespace=False))
                     for line in user_text.split("\n")])
    # Crea l'immagine temporanea per ottenere la dimensione del testo
    _scratch = Image.new("RGBA", (1,1))
    _draw = ImageDraw.Draw(_scratch)
    return text, _draw.textsize(text, font)
    
    
def _prepare_text_overlay(conf, picture_size):
    # Crea font e calcola l'altezza della riga
    font_size = conf.get("font_size", 25)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
    line_height = font.getsize("a")[1] * 1.5

    # Calcola il padding come percentuale dell'altezza della riga
    padding_ratio = conf.get("padding_ratio", 0.2)
    padding = math.ceil(line_height*padding_ratio)
    
    # Rimpiazza %%TIME e %%DATE con i rispettivi valori
    user_text = conf.get("text", "TESTOOOO")
    time_format = conf.get("time_format", "%H:%M:%S")
    user_text = user_text.replace("%%TIME", datetime.datetime.now().strftime(time_format))
    date_format = conf.get("date_format", "%Y-%m-%d")
    user_text = user_text.replace("%%DATE", datetime.datetime.now().strftime(date_format))

    # Calcola la dimensione del testo con il padding
    text, text_size = _process_text(font, user_text, picture_size[1])
    text_size = (text_size[0] + padding * 2, text_size[1] + padding * 2)
    
    # Crea l'immagine
    font_color = conf.get("font_color", (0, 0, 0)) 
    background_color = conf.get("background_color", (255, 255, 255, 0)) 
    label = Image.new("RGBA", text_size, color=background_color)
    draw = ImageDraw.Draw(label)
    draw.text((padding, padding, padding), text, font_color, font=font)
    return label
    
    

def process_picture(raw_picture_name, conf):

    # Dimensioni della foto
    picture = Image.open(raw_picture_name)
    picture_size = picture.size
        
    # Calcola i parametri degli oggetti da sovrapporre
    pieces_to_layout = []
    for text_position, text_conf in conf.get("text", {}).items():
        if text_conf.get("text", None):
            overlay = _prepare_text_overlay(text_conf, picture_size)
            pieces_to_layout.append((text_position, text_conf, overlay))
            
        elif text_conf.get("image", None):
            pass
            
        else:
            pass
            # FIXME REPORT THIS ERROR!!
    
    # Calcola i bordi da aggiungere
    border_top = 0
    border_bottom = 0
    for pos, o_conf, overlay in pieces_to_layout:
        if not o_conf.get("over_the_picture", "NO").upper() == "YES":
            if "top" in pos:
                border_top = max(border_top, overlay.size[1])     
            else:
                border_bottom = max(border_bottom, overlay.size[1])     

    # Genera l'immagine finale aggiungendo bordi per il testo se necessario
    image_size = (picture_size[0], picture_size[1]+border_top+border_bottom)
    image_background_color = conf.get("image_background_color", (0,0,0,0))
    image = Image.new("RGBA", image_size, color=image_background_color)

    # Aggiunge la foto
    image.paste(picture, (0, border_top))

    # Aggiunge gli overlays
    for pos, o_conf, overlay in pieces_to_layout:
        over_picture = o_conf.get("over_the_picture", "NO").upper() == "YES"
        x, y = 0, 0
        if "left" in pos:
            x = 0
        if "right" in pos:
            x = image.size[0]-overlay.size[0]
        if "top" in pos:
            if over_picture:
                y = border_top
            else:
                y = 0
        if "bottom" in pos:
            if over_picture:
                y = image.size[1]-overlay.size[1]-border_bottom
            else:
                y = image.size[1]-overlay.size[1]
        image.paste(overlay, (x, y))

    # Crea il nome dell'immagine
    image_name = conf.get("image_name", "image")
    if not conf.get("add_date_to_image_name", "YES").upper() == "NO":
        image_name = image_name + "_" + datetime.datetime.now().strftime("%Y:%m:%d")
    if not conf.get("add_time_to_image_name", "YES").upper() == "NO":
        image_name = image_name + "_" + datetime.datetime.now().strftime("%H:%M:%S")
    image_name = image_name + ".png"

    # Salva l'immagine
    image.save(image_name)



def send_picture():
    pass


def main():
    # Carica i parametri
    with open("configurazione.json", 'r') as conf:
        configuration = json.load(conf)

    # Scatta la foto
    raw_picture_name = shoot_picture()

    # Scrive sopra
    final_picture_name = process_picture(raw_picture_name, configuration)
    
    # Invia la foto e scarica la nuova configurazione
    send_picture()


if "__main__" == __name__:
    main()


