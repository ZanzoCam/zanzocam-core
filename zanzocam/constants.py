import sys
from pathlib import Path


#
# Paths & local URLs
#

# Executables constants
SYSTEM_USER = "zanzocam-bot"
ZANZOCAM_EXECUTABLE = "/home/zanzocam-bot/venv/bin/z-webcam"

# Base paths
BASE_PATH = Path(__file__).parent
DATA_PATH = BASE_PATH / "data" 

STREAM_FLAG = DATA_PATH / "stream.flag"

# Log files
SERVER_LOG = DATA_PATH / 'error.log'
CAMERA_LOG = DATA_PATH / 'camera.log'
CALIBRATION_LOG = DATA_PATH / 'calibration.log'
FAILURE_REPORT_PATH = DATA_PATH / 'failure_report.txt'

# Configuration file
CONFIGURATION_FILE = DATA_PATH / "configuration.json"

# Setup related files
WIFI_DATA = DATA_PATH / "wifi_data.json"
PICTURE_LOGS = DATA_PATH / "picture_logs.txt"
HOTSPOT_LOGS = DATA_PATH / "hotspot_logs.txt"
CALIBRATION_DATASET = DATA_PATH / "luminance_speed_dataset.csv"
CALIBRATED_PARAMS = DATA_PATH / "calibration_parameters.csv"

# Flags (single value files)
HOTSPOT_FLAG = DATA_PATH / "hotspot.flag"
CALIBRATION_FLAG = DATA_PATH / "calibration.flag"

# Image paths (they have to be served out, so they go in the statics)
PREVIEW_PICTURE_URL =  "static/previews/zanzocam-preview.jpg"
PREVIEW_PICTURE = BASE_PATH / "web_ui" / PREVIEW_PICTURE_URL

CALIBRATION_GRAPH_URL = "static/previews/calibration_graph.png"
CALIBRATION_GRAPH = BASE_PATH / "web_ui" / CALIBRATION_GRAPH_URL

# Camera overlays
IMAGE_OVERLAYS_PATH = DATA_PATH / "overlays"
REMOTE_IMAGES_PATH = "configuration/overlays/"


#
# Constants & defaults
#

# Cronjob constants
TEMP_CRONJOB = DATA_PATH / ".tmp-cronjob-file"
BACKUP_CRONJOB = DATA_PATH / ".crontab.bak"
CRONJOB_FILE = "/etc/cron.d/zanzocam"
TEMP_CALIBRATION_CRONJOB = DATA_PATH / ".tmp-calibration-cronjob-file"
CALIBRATION_CRONJOB_FILE = "/etc/cron.d/zanzocam-calibration"

# System constants
REQUEST_TIMEOUT = 60
CHECK_UPLINK_URL = "http://www.google.com"
AUTOHOTSPOT_BINARY_PATH = "/usr/bin/autohotspot"


#
#  Camera constants
#

# Minimum luminance for the daytime. 
# If the detected luminance goes below this value, the night mode kicks in.
MINIMUM_DAYLIGHT_LUMINANCE = 60

# Minimum luminance to try reaching in very dark conditions.
# The actual luminance of night pictures might be a bit below this value.
MINIMUM_NIGHT_LUMINANCE = 30

# Default parameters for the luminance/shutterspeed interpolation curve.
# Calculated for a Raspberry Pi Camera v1.2
# They can be overridden by custom calibrated parameters.
LUM_SPEED_PARAM_A = 800000
LUM_SPEED_PARAM_B = 200000

# luminance/shutterspeed interpolation: extremes for the shutter speed binary search
MIN_SHUTTER_SPEED = int(0.03 * 10**6)
MAX_SHUTTER_SPEED = int(3 * 10**6)
MULT_SHUTTER_SPEED = 1.5

# Used in the binary search to give some margin to the luminosity
# Matches if luminance = target +- this margin
TARGET_LUMINOSITY_MARGIN = 1

# Fallback values for the camera configuration
CAMERA_DEFAULTS = {
    "name": "no-name",
    "extension": "jpg",
    "time_format": "%H:%M",
    "date_format": "%d %B %Y",
    "width": 100,
    "height": 100,
    "ver_flip": False,
    "hor_flip": False,
    "rotation": 0,
    "jpeg_quality": 90,
    "jpeg_subsampling": 0,
    "background_color": (0,0,0,0),
    "calibrate": False,
}
