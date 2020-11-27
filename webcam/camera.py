#!/usr/bin/python3

import os
import math
import json
import shutil
import requests
import datetime
import textwrap
from pathlib import Path
from picamera import PiCamera
from PIL import Image, ImageFont, ImageDraw


path = Path(__file__).parent


def shoot_picture(image_conf):
    """ Scatta la foto """
    camera = PiCamera()
    camera.resolution = (int(image_conf.get("width", 100)), int(image_conf.get("height", 100)))
    camera.vflip = image_conf.get("ver_flip", False)
    camera.hflip = image_conf.get("hor_flip", False)
    camera.rotation = int(image_conf.get("rotation", 0))
    image_name = '.temp_image.jpg'
    camera.capture(image_name)
    return image_name



def _process_text(font, user_text, max_line_length):
    """ Misura e manda a capo il testo per farlo stare nell'immagine """
    # Manda a capo il testo usando come riferimento la larghezza massima specificata
    lines = []
    for line in user_text.split("\n"):
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
    text = '\n'.join(lines)
    # Crea l'immagine temporanea per ottenere la dimensione finali del testo
    _scratch = Image.new("RGBA", (1,1))
    _draw = ImageDraw.Draw(_scratch)
    return text, _draw.textsize(text, font)


def _prepare_text_overlay(conf, picture_size):
    """ Prepara un overlay contenente un'immagine """
    # Crea font e calcola l'altezza della riga
    font_size = conf.get("font_size", 25)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
    line_height = font.getsize("a")[1] * 1.5

    # Calcola il padding come percentuale dell'altezza della riga
    padding_ratio = conf.get("padding_ratio", 0.2)
    padding = math.ceil(line_height*padding_ratio)

    # Rimpiazza %%TIME e %%DATE con i rispettivi valori
    user_text = conf.get("text", "~~~ DEFAULT TEXT ~~~")
    time_format = conf.get("time_format", "%H:%M:%S")
    user_text = user_text.replace("%%TIME", datetime.datetime.now().strftime(time_format))
    date_format = conf.get("date_format", "%Y-%m-%d")
    user_text = user_text.replace("%%DATE", datetime.datetime.now().strftime(date_format))

    # Calcola la dimensione del testo con il padding
    text, text_size = _process_text(font, user_text, picture_size[0])
    text_size = (text_size[0] + padding * 2, text_size[1] + padding * 2)

    # Crea l'immagine
    font_color = conf.get("font_color", (0, 0, 0))
    background_color = conf.get("background_color", (255, 255, 255, 0))
    label = Image.new("RGBA", text_size, color=background_color)
    draw = ImageDraw.Draw(label)
    draw.text((padding, padding, padding), text, font_color, font=font)
    return label


def _prepare_image_overlay(conf):
    """ Prepara un overlay contenente testo """
    # Calcola il padding come percentuale dell'altezza della dimensione dell'immagine
    picture_name = conf.get("image")
    if not picture_name:
        print("==> Attenzione! Il file di configurazione contiene una entry Image senza nome.")
    try:
        picture = Image.open(path / picture_name)
    except IOError as e:
        print(f"==> Attenzione! Immagine '{picture_name}' non trovata.")

    # Calcola le nuove dimensioni, mantenendo l'aspect ratio se necessario
    width = conf.get("width")
    height = conf.get("height")
    if width and not height:
        old_aspect_ratio = picture.size[0]/picture.size[1]
        height = math.ceil(width/old_aspect_ratio)
    if not width and height:
        old_aspect_ratio = picture.size[1]/picture.size[0]
        width = math.ceil(height/old_aspect_ratio)

    picture = picture.resize((width, height))

    padding_ratio = conf.get("padding_ratio", 0.2)
    padding_width = math.ceil(width*padding_ratio)
    padding_height = math.ceil(height*padding_ratio)

    image_size = (width+padding_width*2, height+padding_height*2)
    background_color = conf.get("background_color", (0, 0, 0, 0))
    image = Image.new("RGBA", image_size, color=background_color)
    image.paste(picture, (padding_width, padding_height), mask=picture)

    return image


def process_picture(raw_picture_name, image_conf, overlays_conf):
    """ Crea l'immagine finale aggiungendo testo e immagini come da configurazione """
    # Dimensioni della foto
    picture = Image.open(raw_picture_name)
    picture_size = picture.size

    # Calcola i parametri degli oggetti da sovrapporre
    pieces_to_layout = []
    for piece_position, piece_conf in overlays_conf.items():
        if piece_conf.get("text"):
            overlay = _prepare_text_overlay(piece_conf, picture_size)
            pieces_to_layout.append((piece_position, piece_conf, overlay))

        elif piece_conf.get("image"):
            overlay = _prepare_image_overlay(piece_conf)
            pieces_to_layout.append((piece_position, piece_conf, overlay))

        else:
            print("==> ERRORE! <==")
            print("Tipo di overlay non riconosciuto. Puoi usare 'text' o 'image'.")

    # Calcola i bordi da aggiungere
    border_top = 0
    border_bottom = 0
    for pos, o_conf, overlay in pieces_to_layout:
        if not o_conf.get("over_the_picture", False):
            if "top" in pos:
                border_top = max(border_top, overlay.size[1])
            else:
                border_bottom = max(border_bottom, overlay.size[1])

    # Genera l'immagine finale aggiungendo bordi per il testo se necessario
    image_size = (picture_size[0], picture_size[1]+border_top+border_bottom)
    image_background_color = image_conf.get("background_color", (0,0,0,0))
    image = Image.new("RGBA", image_size, color=image_background_color)

    # Aggiunge la foto
    image.paste(picture, (0, border_top))

    # Aggiunge gli overlays
    for pos, o_conf, overlay in pieces_to_layout:
        over_picture = o_conf.get("over_the_picture", False)
        x, y = 0, 0
        if "left" in pos:
            x = 0
        if "right" in pos:
            x = image.size[0]-overlay.size[0]
        if "center" in pos:
            x = int((image.size[0]-overlay.size[0])/2)
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
        image.paste(overlay, (x, y), mask=overlay)  # mask is to allow for transparent images

    # Crea il nome dell'immagine
    image_name = image_conf.get("name", "image")
    image_extension = image_conf.get("extension", "jpg")
    if image_conf.get("add_date_to_name", True):
        image_name += "_" + datetime.datetime.now().strftime("%Y-%m-%d")
    if image_conf.get("add_time_to_name", True):
        image_name += "_" + datetime.datetime.now().strftime("%H:%M:%S")
    image_name = image_name + "." + image_extension

    # Salva l'immagine
    image.save(image_name)
    return image_name


def send_picture_and_get_config(image_name, url):
    """ Invia l'immagine al server con una POST. """
    # Carica i logs
    logs = " ==> No logs found. <== "
    with open(path/"logs.txt", "r+") as l:
        logs = l.readlines()

    # Backup del file di configurazione precedente
    shutil.copy(path / "configurazione.json", path / "configurazione.prev.json")

    # Invia la POST
    user = os.environ.get("RPICAM_SERVER_USERNAME", "")
    pwd = os.environ.get("RPICAM_SERVER_PWD", "")
    
    files = {'photo': open(image_name, 'rb')}
    data = {'logs': logs}
    response = requests.post(url, data=data, files=files, auth=requests.auth.HTTPBasicAuth(user, pwd))

    # Aggiorna il file di configurazione
    try:
        new_config = json.loads(response.content.decode('utf-8'))
        with open(path / "configurazione.json", 'w') as conf:
            json.dump(new_config, conf, indent=4)
    except:
        print("==> ERRORE! <==")
        print("Qualcosa e' andato storto nello scaricare il file di configurazione! Il file contiene:")
        print(response.content.decode('utf-8'))


def main():
    print("\n==========================================")
    print(f"===> Avvio: {datetime.datetime.now()}")
    # Carica i parametri
    with open(path / "configurazione.json", 'r') as c:
        conf = json.load(c)

        print(f"File di configurazione utilizzato:")
        print(json.dumps(conf, indent=4))

        # Scatta la foto
        raw_pic_name = shoot_picture(conf.get("image", {}))
        print(f"===> Foto scattata: {datetime.datetime.now()} ")

        # Scrive sopra
        final_pic_name = process_picture(raw_pic_name, conf.get("image", {}), conf.get("overlays", {}))
        print(f"===> Immagine finale pronta: {datetime.datetime.now()} ")

        # Invia la foto e scarica la nuova configurazione
        url = conf.get("server_url")
        send_picture_and_get_config(final_pic_name, url)
        print(f"===> Upload completato: {datetime.datetime.now()}")

        # Cancella la foto
        os.remove(raw_pic_name)
        os.remove(final_pic_name)

        # Aggiorna il crontab
        #cronjob_triggers = configuration.get("cronjob_triggers", "")
        #os.system("crontab -l > .last-cronjob")
        #os.system(f"echo '{cronjob_triggers} python3 /home/pi/webcam/camera.py > /home/pi/logs.txt 2>&1' >> .last-cronjob")
        #os.system("crontab .last-cronjob")


if "__main__" == __name__:
    main()


