# pylint: disable=missing-function-docstring

import os
import sys
import logging
from flask import Flask, render_template, redirect, url_for, abort, request

import zanzocam.constants as constants
from zanzocam.web_ui import pages, api


app = Flask(__name__)


# Prevent caching: can break the logs fetching client-side
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-store"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    return r


# Setup the logging
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.FileHandler(constants.SERVER_LOG),
        logging.StreamHandler(sys.stdout),
    ],
    format='%(asctime)s,%(msecs)-4d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S'
)


#
# Pages
#

@app.route("/", methods=["GET"])
def home_endpoint():
    return pages.home_page()


@app.route("/server", methods=["GET"])
def server_endpoint():
    return pages.server_page()


@app.route("/webcam", methods=["GET"])
def webcam_endpoint():
    return pages.webcam_page()


@app.route("/logs", methods=["GET"])
def logs_endpoint():
    return pages.logs_page()


#
# API for setting configuration values
#

@app.route("/configure/server", methods=["POST"])
def configure_server_endpoint():
    api.configure_server(request.form)
    return redirect(url_for('home_endpoint'))
    

@app.route("/configure/send-logs/<value>", methods=["POST"])
def toggle_send_logs_endpoint(value):
    return api.toggle_send_logs(value)


@app.route("/configure/upload-interval/<value>", methods=["POST"])
def set_upload_interval__endpoint(value):
    return api.set_upload_interval(value)


#
# API to take actions
#

@app.route("/reboot", methods=["GET"])
def reboot_endpoint():
    return "", api.reboot()


@app.route("/shoot-picture", methods=["POST"])
def shoot_picture_endpoint():
    return "", api.shoot_picture()


#
# API to fetch data
#

@app.route("/picture-preview", methods=["GET"])
def get_preview_endpoint():
    return api.get_preview()


@app.route("/logs/<kind>/<name>", methods=["GET"])
def get_logs_endpoint(kind: str, name: str):
    if kind in ["json", "text"]:
        return api.get_logs(kind, name)
    abort(404)


@app.route("/logs/all", methods=["GET"])
def get_all_logs_endpoint():
    return api.get_all_logs()


@app.route("/logs/cleanup", methods=["GET"])
def delete_all_logs_endpoint():
    for logfile in os.listdir(constants.CAMERA_LOGS):
        os.remove(constants.CAMERA_LOGS / logfile)
    return redirect(url_for("logs_endpoint"))


#
# Error handlers
#

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


#
# Main
#

def main():    
    app.run(host="0.0.0.0", port=80, debug=False)


if __name__ == "__main__":
    main()

