import sys
from pathlib import Path


VERSION = "0.10.2"


#
# Paths & local URLs
#

# Executables constants
SYSTEM_USER = "zanzocam-bot"
ZANZOCAM_EXECUTABLE = "/home/zanzocam-bot/venv/bin/z-webcam"

# Base paths
BASE_PATH = Path(__file__).parent
DATA_PATH = BASE_PATH / "data" 

# Log files
SERVER_LOG = DATA_PATH / 'interface.log'
CAMERA_LOG = DATA_PATH / 'camera.log'
DIAGNOSTICS_LOG = DATA_PATH / 'diagnostics.log'
FAILURE_REPORT_PATH = DATA_PATH / 'failure_report.txt'

# Configuration file
CONFIGURATION_FILE = DATA_PATH / "configuration.json"

# Setup related files
NETWORK_DATA = DATA_PATH / "network_data.json"
PICTURE_LOGS = DATA_PATH / "picture_logs.txt"
HOTSPOT_LOGS = DATA_PATH / "hotspot_logs.txt"

# Flags (single value files)
HOTSPOT_FLAG = DATA_PATH / "hotspot.flag"

# Image paths (they have to be served out, so they go in the statics)
PREVIEW_PICTURE_URL =  "static/previews/zanzocam-preview.jpg"
PREVIEW_PICTURE = BASE_PATH / "web_ui" / PREVIEW_PICTURE_URL

# Camera overlays
IMAGE_OVERLAYS_PATH = DATA_PATH / "overlays"
REMOTE_IMAGES_PATH = "configuration/overlays/"


#
# Constants & defaults
#

LOCALE = 'it_IT.utf8'
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
WAIT_AFTER_CAMERA_FAIL = 30

# Cronjob constants
TEMP_CRONJOB = DATA_PATH / ".tmp-cronjob-file"
BACKUP_CRONJOB = DATA_PATH / ".crontab.bak"
CRONJOB_FILE = "/etc/cron.d/zanzocam"

# System constants
REQUEST_TIMEOUT = 60
CHECK_UPLINK_URL = "http://www.google.com"
AUTOHOTSPOT_BINARY_PATH = "/usr/bin/autohotspot"

# Server constants
FTP_CONFIG_FILE_ENCODING = 'utf-8'



#
#  Camera constants
#

# Minimum luminance for the daytime. 
# If the detected luminance goes below this value, the night mode kicks in.
MINIMUM_DAYLIGHT_LUMINANCE = 60

# Minimum luminance to target for pictures in low light conditions.
MINIMUM_NIGHT_LUMINANCE = 30

# Starting ISO level for low light pictures
INITIAL_LOW_LIGHT_ISO = 400  

# When to consider the image totally black, where the low light estimation doesn't work well
NO_LUMINANCE_THRESHOLD = 1  

# What "random" shutter speed to use if the image is so black that the equation doesn't work
NO_LUMINANCE_SHUTTER_SPEED = 2 * 10**6 

# Min shutter speed for low light, the max that PiCamera would use with automatic settings
MIN_SHUTTER_SPEED = int(0.03 * 10**6)

# Max shutter speed allowed by the camera hardware 
MAX_SHUTTER_SPEED = int(9.5 * 10**6)

# How much tolerance to give to the low light search algorithm
TARGET_LUMINOSITY_MARGIN = 3

# Time to allow the firmware to compute the right exposure in normal 
# light conditions (AWB requires more)
CAMERA_WARM_UP_TIME = 5

# White balancin modes from picamera
PICAMERA_AWB_MODES = [
    'off',
    'auto',
    'sunlight',
    'cloudy',
    'shade',
    'tungsten',
    'fluorescent',
    'incandescent',
    'flash',
    'horizon',
]

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
    "awb_mode": 'auto',

    # These two are "experimental" and mostly untested, 
    # don't use them unless really necessary
    'use_low_light_algorithm': True,
    'let_awb_settle_in_dark': False,
}

OVERLAY_DEFAULTS = {
    "font_size": 30,
    "padding": 50,
    "text": "... testo ...",
    "font_color": (0, 0, 0),
    "background_color": (255, 255, 255, 0),
    "image": None,
    "width": None,   # Might be unset to retain aspect ratio
    "heigth": None,  # Might be unset to retain aspect ratio
    "over_the_picture": False,
}
