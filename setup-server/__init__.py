import os
import sys
import json
import subprocess
import ansible_runner
from pathlib import Path
from flask import Flask, render_template, request

app = Flask(__name__)



initial_data = "/var/www/setup-server/setup_server/initial_data.json"
log_buffer = "/var/www/setup-server/setup_server/logs.txt"



def clear_logs():
    with open(log_buffer, 'w') as d:
        pass

def log(message, dot="- "):
    with open(log_buffer, 'a') as d:
        d.writelines(f"{dot}{message}\n")
    
    
    

@app.route("/", methods=["GET"])
def setup():
    """ The initial page with the form """
    clear_logs()
    
    # Load any previously stored initial data
    try:
        with open(initial_data, 'r') as d:
            data = json.load(d)
    except Exception:
        data = {}
    return render_template("setup.html", title="Setup", data=data)
    


@app.route("/setting-up", methods=["POST"])
def setting_up():
    """ The page with the logs """
    clear_logs()
    
    # Save new initial data to a file
    with open(initial_data, 'w') as d:
        json.dump(request.form, d, indent=4)
        
    return render_template("setting-up.html", title="Setup")
        

@app.route("/setup/logs", methods=["GET"])
def get_logs():
    """ Endpoint for fetching the latest logs"""
    global log_buffer
    with open(log_buffer, 'r') as d:
        logs = d.readlines()
    return json.dumps(logs)
    

@app.route("/setup/start", methods=["POST"])
def start_setup():
    """ Actually sets up the Pi """
    
    try:
        with open(initial_data, 'r') as d:
            data = json.load(d)
    except Exception:
        abort(404)  # Data must be there!
        
    error=False
    
    # Encrypts the rpi password to make it a valid Linux user password
    # Depends on the 'whois' system package
    #log("Hashing della password")
    #hashing_proc = subprocess.run(["/usr/bin/mkpasswd", "--method=sha-512", data['rpi_password']], stdout=subprocess.PIPE)
    #hashed_password = hashing_proc.stdout.decode('utf-8').strip()
    
    
    log("Setup WiFi")
    with open(".tmp-wpa_supplicant", "w") as f:
            f.writelines(f"""
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={{
    ssid="{data['wifi_ssid']}"
    psk="{data['wifi_password']}"
}}
""")
    create_wpa_conf = subprocess.run(["/usr/bin/sudo", "mv", ".tmp-wpa_supplicant", 
        "/etc/wpa_supplicant/wpa_supplicant.conf"], stdout=subprocess.PIPE)
    if not create_wpa_conf:
        log(f"""ERRORE! Non e' stato possibile configurare il WiFi. 
Usa SSH per configurarlo manualmente:
 - Apri il file con: sudo nano /etc/wpa_supplicant/wpa_supplicant.conf 
 - Copiaci dentro: 

ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={{
    ssid="{data['wifi_ssid']}"
    psk="{data['wifi_password']}"
}}

""",  dot="\n===> ")
        error=True
    
    
    log("Aggiornamento cronjob")
    cron_string = " ".join([
        data['crontab_minute'],
        data['crontab_hour'],
        data['crontab_day'],
        data['crontab_month'], 
        data['crontab_weekday']
    ])
    with open(".tmp-cronjob-file", 'w') as d:
        d.writelines(f"""
# ZANZOCAM - shoot pictures
{cron_string} zanzocam-bot cd /home/zanzocam-bot/webcam && /home/zanzocam-bot/webcam/venv/bin/python3 /home/zanzocam-bot/webcam/camera.py > /home/zanzocam-bot/webcam/logs.txt 2>&1
""") 
    create_cron = subprocess.run(
        ["/usr/bin/sudo", "mv", ".tmp-cronjob-file", "/etc/cron.d/zanzocam"], 
        stdout=subprocess.PIPE)
    if not create_cron:
        log("""ERRORE! Non e' stato possibile creare il cronjob. 
Usa SSH per crearlo manualmente:
 - Apri il file con: sudo nano /etc/cron.d/zanzocam
 - Copiaci dentro: {cron_string} zanzocam-bot cd /home/zanzocam-bot/webcam && /home/zanzocam-bot/webcam/venv/bin/python3 /home/zanzocam-bot/webcam/camera.py > /home/zanzocam-bot/webcam/logs.txt 2>&1\n""",
 dot="\n===> ")
        error = True
        
        
    log("Aggiornamento configurazione della webcam")
    webcam_minimal_conf = {
        "server_url": data['server_url'],
        "server_username": data['server_username'],
        "server_password": data['server_password'],
    }
    try:
        with open("/home/zanzocam-bot/webcam/configuration.json", 'w') as d:
            json.dump(webcam_minimal_conf, d)
    except Exception:
        error = True
        
    if error:
        log("Setup fallito")
        abort(500)
        
    log("Setup completo")
    return json.dumps(True), 200
    
    
    
    

class RedirectText:
    """ Per ottenere i logs di Ansible """
    def __init__(self, logger):
        self.output = logger
    
    def flush(self):
        pass
        
    def write(self, string):
        if ("fatal" in string or "ERROR!" in string) and "ignoring" not in string:
            self.output(f"ERRORE!  {string}", dot="\n===> ")
        if "TASK" in string:
            string = string.replace("*", "")
            string = string.replace("TASK [", " ")
            string = string.replace("]", "")
            string = string.strip()                
            if string != "" and not "ok: " in string:
                self.output(string, dot="  ->")





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

        
