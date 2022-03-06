import sys
from pathlib import Path


#: ZanzoCam version
VERSION = "1.3.0"


# Executables constants
# #####################

#: Main user of the system, must be able to perform a passwordless sudo
SYSTEM_USER = "zanzocam-bot"

#: Location of the z-webcam executable
ZANZOCAM_EXECUTABLE = "/home/zanzocam-bot/venv/bin/z-webcam"


# Base paths
# ##########

#: Folder containing the source code
BASE_PATH = Path(__file__).parent

#: Folder containing the data used by the ZanzoCam for its operations
DATA_PATH = BASE_PATH / "data"


# Log files
# #########

#: Whether to upload the logs to the server at the end of the run.
UPLOAD_LOGS = True

#: Logs of the local server (stay on disk and get rotated)
SERVER_LOG = DATA_PATH / 'interface.log'

#: Logs produced during the main procedure (will be sent to the server)
CAMERA_LOG = DATA_PATH / 'camera.log'

#: Logs produced in case of issues with the server
FAILURE_REPORT_PATH = DATA_PATH / 'failure_report.txt'

#: Main configuration file
CONFIGURATION_FILE = DATA_PATH / "configuration.json"

#: Information about the Internet connection
NETWORK_DATA = DATA_PATH / "network_data.json"

#: (probably unused, TO CHECK)
PICTURE_LOGS = DATA_PATH / "picture_logs.txt"

#: (probably unused, TO CHECK)
HOTSPOT_LOGS = DATA_PATH / "hotspot_logs.txt"

#: Whether the hotspot is allowed
HOTSPOT_FLAG = DATA_PATH / "hotspot.flag"

#: URL to the preview picture in the web UI
PREVIEW_PICTURE_URL = "static/previews/zanzocam-preview.jpg"

#: Path to the preview picture in the web UI
PREVIEW_PICTURE = BASE_PATH / "web_ui" / PREVIEW_PICTURE_URL

#: Local camera overlays path
IMAGE_OVERLAYS_PATH = DATA_PATH / "overlays"

#: Remote camera overlays path
REMOTE_IMAGES_PATH = "configuration/overlays/"


# Constants & defaults
# ####################

#: Locale
LOCALE = 'it_IT.utf8'

#: Path to the default font (can be customized if you install another font)
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

#: Time to wait in between failed shots of the camera
#:  (to overcome colliding crontabs)
WAIT_AFTER_CAMERA_FAIL = 30

#: Temporary crontab path
TEMP_CRONJOB = DATA_PATH / ".tmp-cronjob-file"

#: Path to the crontab's backup
BACKUP_CRONJOB = DATA_PATH / ".crontab.bak"

#: Path to the system crontab
CRONJOB_FILE = "/etc/cron.d/zanzocam"

#: Timeout for HTTP requests
REQUEST_TIMEOUT = 60

#: URL to check to ensure Internet is reachable
CHECK_UPLINK_URL = "http://www.google.com"

#: Path to the autohotspot script
AUTOHOTSPOT_BINARY_PATH = "/usr/bin/autohotspot"

#: Ecoding of the FTP server files
FTP_CONFIG_FILE_ENCODING = 'utf-8'


# Camera constants
# ################

#: Minimum luminance for the daytime.
#:  If the detected luminance goes below this value, the night mode kicks in.
MINIMUM_DAYLIGHT_LUMINANCE = 60

#: Minimum luminance to target for pictures in low light conditions.
MINIMUM_NIGHT_LUMINANCE = 30

#: Starting ISO level for low light pictures
INITIAL_LOW_LIGHT_ISO = 400

#: When to consider the image totally black,
#:  where the low light estimation doesn't work well
NO_LUMINANCE_THRESHOLD = 1

#: What "random" shutter speed to use if the image
#:  is so black that the equation doesn't work
NO_LUMINANCE_SHUTTER_SPEED = 2 * 10**6

#: Min shutter speed for low light, the
#:  max that PiCamera would use with automatic settings
MIN_SHUTTER_SPEED = int(0.03 * 10**6)

#: Max shutter speed allowed by the camera hardware
MAX_SHUTTER_SPEED = int(9.5 * 10**6)

#: How much tolerance to give to the low light search algorithm
TARGET_LUMINOSITY_MARGIN = 3

#: Time to allow the firmware to compute the right exposure in normal
#:  light conditions (AWB requires more)
CAMERA_WARM_UP_TIME = 5

#: White balancing modes from picamera
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

#: Fallback values for the camera configuration
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
    "background_color": (0, 0, 0, 0),
    "awb_mode": 'auto',

    # These two are "experimental" and mostly untested,
    # don't use them unless really necessary
    'use_low_light_algorithm': True,
    'let_awb_settle_in_dark': False,
}

#: Fallback values for the image overlays
OVERLAY_DEFAULTS = {
    "font_size": 30,
    "padding": 10,
    "text": "... testo ...",
    "font_color": (0, 0, 0),
    "background_color": (255, 255, 255, 0),
    "image": None,
    "width": None,   # Might be unset to retain aspect ratio
    "heigth": None,  # Might be unset to retain aspect ratio
    "over_the_picture": False,
}
