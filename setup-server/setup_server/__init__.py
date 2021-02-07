import os
import sys
import json
import subprocess
from pathlib import Path
from textwrap import dedent
from flask import Flask, render_template, request, abort, send_fron_directory

app = Flask(__name__)


INITIAL_DATA = "/var/www/setup-server/setup_server/initial_data.json"
LOG_BUFFER = "/var/www/setup-server/setup_server/logs.txt"



def clear_logs():
    with open(LOG_BUFFER, 'w') as d:
        pass

def log(message, dot="- "):
    with open(LOG_BUFFER, 'a') as d:
        d.writelines(f"{dot}{message}\n")



@app.route("/", methods=["GET"])
def setup():
    """ The initial page with the form """
    clear_logs()
    # Load any previously stored initial data
    try:
        with open(INITIAL_DATA, 'r') as d:
            data = json.load(d)
    except Exception:
        data = {}
    return render_template("setup.html", title="Setup", data=data)


@app.route("/hotspot/<value>", methods=["POST"])
def toggle_hotspot(value):
    """ Allow the hotspot to turn on or not """
    if value in ["ON", "OFF"]:
        try:
            with open("/home/zanzocam-bot/HOTSPOT_ALLOWED", "w") as f:
                f.write(value)
            
            data = {}
            with open(INITIAL_DATA, 'r') as d:
                data = json.load(d)
            data["hotspot_allowed"] = value
            with open(INITIAL_DATA, 'w') as d:
                json.dump(data, d, indent=4)

        except Exception:
            abort(500)
    abort(404)



@app.route("/setting-up", methods=["POST"])
def setting_up():
    """ The page with the logs """
    clear_logs()
    # Save new initial data to a file
    with open(INITIAL_DATA, 'w') as d:
        json.dump(request.form, d, indent=4)
    return render_template("setting-up.html", 
        title="Setup",
        initial_message="Preparazione setup",
        progress_message="Setup in corso (non lasciare la pagina!)",
        dont_leave_message="Il setup non è ancora completo!",
        async_url="/setup/start",
        async_process_completed_message_short="Setup completato!",
        async_process_completed_message_long="Setup completato! "+
                    "Riavvia il Raspberry Pi se non è ancora collegato alla "+
                    "rete da te specificata, poi configura il tuo server e infine " +
                    "scatta una foto di prova per far partire la webcam.",
        async_process_failed_message_short="Setup fallito!",
        async_process_failed_message_long="Il setup non è andato a buon fine. Controlla i log "+
                "prima di lasciare la pagina e riprova.",
        )


@app.route("/logs", methods=["GET"])
def get_logs():
    """ Endpoint for fetching the latest logs as JSON"""
    global LOG_BUFFER
    with open(LOG_BUFFER, 'r') as d:
        logs = d.readlines()
    return json.dumps(logs)


@app.route("/logs-download", methods=["GET"])
def get_logs_2():
    """ Endpoint for downloading the latest logs as a text file"""
    global LOG_BUFFER
    return send_from_directory("/".join(LOG_BUFFER.split("/")[:-1]), LOG_BUFFER.split("/")[-1])


@app.route("/setup/start", methods=["POST"])
def start_setup():
    """ Actually sets up the Pi """
    try:
        with open(INITIAL_DATA, 'r') as d:
            data = json.load(d)
    except Exception:
        abort(404)  # Data must be there!

    # Write the wpa_supplicant.conf file
    error=False
    log("Setup WiFi")
    with open(".tmp-wpa_supplicant", "w") as f:
        f.writelines(dedent(f"""
            ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
            update_config=1

            network={{
                ssid="{data['wifi_ssid']}"
                psk="{data['wifi_password']}"
            }}
            """))
    create_wpa_conf = subprocess.run(
        [
            "/usr/bin/sudo",
            "mv",
            ".tmp-wpa_supplicant",
            "/etc/wpa_supplicant/wpa_supplicant.conf"
        ],
        stdout=subprocess.PIPE)
    if not create_wpa_conf:
        log(dedent(f"""ERRORE! Non è stato possibile configurare il WiFi.
                Usa SSH per configurarlo manualmente:
                 - Apri il file con: sudo nano /etc/wpa_supplicant/wpa_supplicant.conf
                 - Copiaci dentro:

                ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
                update_config=1

                network={{
                    ssid="{data['wifi_ssid']}"
                    psk="{data['wifi_password']}"
                }}"""),  dot="\n===> ")
        error=True

    # Write the initial configuration.json to bootstrap the webcam
    log("Setup dati del server remoto")
    webcam_minimal_conf = {
        "server": {
            "protocol": data['server_protocol'],
            "username": data['server_username'],
            "password": data['server_password']
        }
    }
    if data['server_protocol'] == "FTP":
        webcam_minimal_conf["server"]["hostname"] = data["server_hostname"]
        webcam_minimal_conf["server"]["subfolder"] = data.get("server_subfolder")
        webcam_minimal_conf["server"]["tls"] = data.get("server_tls", False)
    else:
        webcam_minimal_conf["server"]["url"] = data["server_url"]
    try:
        with open("/home/zanzocam-bot/webcam/configuration.json", 'w') as d:
            json.dump(webcam_minimal_conf, d, indent=4)
    except Exception as e:
        error = True

    # If there was an error at some point, return 500
    if error:
        log("Setup fallito")
        abort(500)

    log("Setup completo")
    return json.dumps(True), 200



@app.route("/shoot-picture")
def shoot():
    """ The page where a picture can be shoot """
    clear_logs()
    return render_template("setting-up.html", 
        camera=True,
        title="Scatta Foto",
        initial_message="Preparazione scatto foto",
        progress_message="ZANZOCAM sta scattando (non lasciare la pagina!)",
        dont_leave_message="La foto non è ancora stata scattata!",
        async_url="/shoot-picture/start",
        async_process_completed_message_short="Foto scattata!",
        async_process_completed_message_long="Foto scattata! Vai sul tuo server per assicurarti che sia arrivata.",
        async_process_failed_message_short="Foto non scattata!",
        async_process_failed_message_long="Lo scatto della foto non è andato a buon fine. "+
                "Verifica che tutti i parametri siano corretti e controlla i log per capire cosa non ha funzionato.",
        )


@app.route("/shoot-picture/start", methods=["POST"])
def start_shoot():
    """ Actually shoots the picture """
    error = False
    try:
        with open(INITIAL_DATA, 'r') as d:
            data = json.load(d)

        try:
            with open(LOG_BUFFER, 'w') as l:                
                shoot_proc = subprocess.Popen(["/home/zanzocam-bot/venv/bin/z-webcam"], stdout=l, stderr=l)

        except subprocess.CalledProcessError as e:
            error = "Il processo ha generato un errore: " + str(e)

    except Exception as e:
        error = "Si è verificato un errore inaspettato: " + str(e)

    # If there was an error at some point, return 500
    if error:
        with open(LOG_BUFFER, 'a') as l:
            l.writelines(error)
        abort(500)

    return "", 200



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
