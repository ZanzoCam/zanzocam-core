import os
import sys
import json
import subprocess
from pathlib import Path
from textwrap import dedent
from flask import Flask, render_template, request, abort, send_from_directory, redirect, url_for

app = Flask(__name__)


HOTSPOT_FLAG = "/home/zanzocam-bot/webcam/HOTSPOT_ALLOWED"
WIFI_DATA = "/var/www/setup-server/setup_server/config/wifi_data.json"
SERVER_DATA = "/var/www/setup-server/setup_server/config/server_data.json"

PICTURE_LOGS = "/var/www/setup-server/setup_server/config/picture_logs.txt"
HOTSPOT_LOGS = "/var/www/setup-server/setup_server/config/hotspot_logs.txt"

PREVIEW_IMAGE =  "/var/www/setup-server/setup_server/static/previews/zanzocam-preview.jpg"
PREVIEW_URL =  "/static/previews/zanzocam-preview.jpg"



@app.route("/", methods=["GET"])
def setup(feedback=None, feedback_sheet_name=None, feedback_type=None):
    """ The initial page with the forms """

    try:
        with open(WIFI_DATA, 'r') as d:
            wifi_data = json.load(d)
    except Exception as e:
        print(e)
        wifi_data = {}

    try:
        with open(SERVER_DATA, 'r') as d:
            config_stub = json.load(d)
    except Exception as e:
        print(e)
        config_stub = {}
    server_data = config_stub.get('server', {})

    try:
        with open(HOTSPOT_FLAG, 'r') as d:
            hotspot_value = d.read()
    except Exception as e:
        print(e)
        hotspot_value = "ON"

    return render_template("setup.html", 
                                title="Setup Iniziale", 
                                wifi_data=wifi_data, 
                                server_data=server_data, 
                                hotspot_value=hotspot_value,
                                feedback=feedback,
                                feedback_sheet_name=feedback_sheet_name,
                                feedback_type=feedback_type,
)


@app.route("/configure-wifi", methods=["POST"])
def configure_wifi():
    """ Save the WiFi data and run the hotspot script """
    
    ssid = request.form["wifi_ssid"]
    password = request.form["wifi_password"]

    wifi_data = {
        "ssid": ssid,
        "password": password
    }

    with open(WIFI_DATA, "w") as w:
        json.dump(wifi_data, w)
    
    with open(".tmp-wpa_supplicant", "w") as f:
        f.writelines(dedent(f"""
            ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
            update_config=1

            network={{
                ssid="{ssid}"
                psk="{password}"
            }}
            """))
    create_wpa_conf = subprocess.run(
        [
            "/usr/bin/sudo",
            "mv",
            ".tmp-wpa_supplicant",
            "/etc/wpa_supplicant/wpa_supplicant.conf"
        ])
    try:
        with open(HOTSPOT_LOGS, 'w') as l:                
            autohotspot = subprocess.Popen(["/usr/bin/autohotspot"], stdout=l, stderr=l)

    except subprocess.CalledProcessError as e:
        return redirect(url_for('setup', feedback=f"Si e' verificato un errore: {e}", feedback_sheet_name="wifi", feedback_type="negative"))

    return redirect(url_for('setup', feedback="Wifi configurato con successo", feedback_sheet_name="wifi", feedback_type="positive"))


@app.route("/configure-server", methods=["POST"])
def configure_server():
    """ Save the server data """

    webcam_minimal_conf = {
        "server": {
            "protocol": request.form['server_protocol'],
            "username": request.form['server_username'],
            "password": request.form['server_password']
        }
    }
    if request.form['server_protocol'] == "FTP":
        webcam_minimal_conf["server"]["hostname"] = request.form["server_hostname"]
        webcam_minimal_conf["server"]["subfolder"] = request.form.get("server_subfolder")
        webcam_minimal_conf["server"]["tls"] = request.form.get("server_tls", False)
    else:
        webcam_minimal_conf["server"]["url"] = request.form["server_url"]

    try:
        with open("/home/zanzocam-bot/webcam/configuration.json", 'w') as d:
            json.dump(webcam_minimal_conf, d, indent=4)
    except Exception as e:
        return redirect(url_for('setup', feedback=f"Si e' verificato un errore nel salvare i dati del server: {e}", feedback_sheet_name="server", feedback_type="negative"))

    try:
        with open(SERVER_DATA, 'w') as d:
            json.dump(webcam_minimal_conf, d, indent=4)
    except Exception as e:
        return redirect(url_for('setup', feedback=f"Si e' verificato un errore nel salvare i dati del server: {e}", feedback_sheet_name="server", feedback_type="negative"))

    return redirect(url_for('setup', feedback="Server configurato con successo", feedback_sheet_name="server", feedback_type="positive"))



@app.route("/hotspot/<value>", methods=["POST"])
def toggle_hotspot(value):
    """ Allow the hotspot to turn on or not """
    if value in ["ON", "OFF"]:
        try:
            with open(HOTSPOT_FLAG, "w") as f:
                f.write(value)
            return f"Hotspot set to {value}", 200
            
        except Exception:
            abort(500)
    abort(404)



@app.route("/setup-webcam")
def setup_webcam():
    """ The page where a picture can be shoot """
    # Should be cleaned up immediately, or they're gonna show in the textarea at the beginning
    global PICTURE_LOGS
    clear_logs(PICTURE_LOGS)    

    return render_template("setup-webcam.html", title="Setup Webcam", preview_url=PREVIEW_URL)


@app.route("/preview-picture")
def preview():
    take_preview_picture = subprocess.run(
        ["/usr/bin/raspistill", "-w", "800", "-h", "550", "-o", PREVIEW_IMAGE ])
    return send_from_directory("/".join(PREVIEW_IMAGE.split("/")[:-1]), PREVIEW_IMAGE.split("/")[-1])    # Actually the image will be refreshed by Javascript


@app.route("/shoot-picture")
def shoot():
    """ Actually shoots the picture """
    global PICTURE_LOGS
    clear_logs(PICTURE_LOGS)    

    try:
        with open(PICTURE_LOGS, 'w') as l:                
            shoot_proc = subprocess.run(["/home/zanzocam-bot/venv/bin/z-webcam"], stdout=l, stderr=l)
            
    except subprocess.CalledProcessError as e:
        with open(PICTURE_LOGS, 'a') as l:
            l.writelines(f"Si e' verificato un errore: {e}")
        abort(500)

    return "OK", 200



def clear_logs(logs_path):
    with open(logs_path, 'w') as d:
        pass


@app.route("/logs/<kind>/<name>", methods=["GET"])
def get_logs(kind: str, name: str):
    """ Endpoint for fetching the latest logs """
    logs_path = None

    if name == "hotspot":
        global HOTSPOT_LOGS
        logs_path = HOTSPOT_LOGS
    
    elif name == "picture":
        global PICTURE_LOGS
        logs_path = PICTURE_LOGS

    else:
        return f"Logs not found for name {name}", 500

    if kind == "json":
        logs = {"content": ""}
        try:
            with open(logs_path, 'r') as d:
                logs["content"] = "".join(d.readlines())

        except FileNotFoundError:
            with open(logs_path, "w"):
                pass

        return logs

    elif kind == "text":
        if not os.path.exists(logs_path):
            with open(logs_path, "w"):
                pass
        return send_from_directory("/".join(logs_path.split("/")[:-1]), logs_path.split("/")[-1])

    else:
        return f"Logs type {kind} not understood", 500
    




@app.errorhandler(400)
def handle_bad_request(e):
    return render_template("error.html", title="400", message="400 - Bad Request"), 400

@app.errorhandler(401)
def handle_unauthorized(e):
    return render_template("error.html", title="401", message="401 - Unauthorized"), 401

@app.errorhandler(403)
def handle_forbidden(e):
    return render_template("error.html", title="403", message="403 - Forbidden"), 403

@app.errorhandler(404)
def handle_not_found(e):
    return render_template("error.html", title="404", message="404 - Not Found"), 404

@app.errorhandler(405)
def handle_method_not_allowed(e):
    return render_template("error.html", title="405", message="405 - Method Not Allowed"), 405

@app.errorhandler(500)
def handle_internal_error(e):
    return render_template("error.html", title="500", message="500 - Internal Server Error"), 500
