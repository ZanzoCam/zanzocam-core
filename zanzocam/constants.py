from pathlib import Path

# Base paths
BASE_PATH = Path(__file__).parent
DATA_PATH = BASE_PATH / "data" 

# Log files
SERVER_LOG = DATA_PATH / 'error.log'
CAMERA_LOG = DATA_PATH / 'error.log'

# Configuration file
CONFIGURATION_FILE = DATA_PATH / "configuration.json"

# Setup related files
WIFI_DATA = DATA_PATH / "wifi_data.json"
PICTURE_LOGS = DATA_PATH / "picture_logs.txt"
HOTSPOT_LOGS = DATA_PATH / "hotspot_logs.txt"
CALIBRATION_DATASET = DATA_PATH / "luminance_speed_table.csv"
CALIBRATED_PARAMS = DATA_PATH / "calibration_parameters.csv"

# Flags (single value files)
HOTSPOT_FLAG = DATA_PATH / "hotspot.flag"
CALIBRATION_FLAG = DATA_PATH / "calibration.flag"

# Image paths (they have to be served out, so they go in the statics)
PREVIEW_PICTURE_URL =  "/static/previews/zanzocam-preview.jpg"
PREVIEW_PICTURE = BASE_PATH / "web_ui" / PREVIEW_PICTURE_URL

CALIBRATION_GRAPH_URL = "/static/previews/calibration_graph.png"
CALIBRATION_GRAPH = BASE_PATH / "web_ui" / CALIBRATION_GRAPH_URL

