from pathlib import Path


PATH = Path(__file__).parent.parent

CONFIGURATION_PATH = PATH / "configuration.json"
CONFIGURATION_BACKUP_PATH = PATH / "configuration.json.bak"

IMAGE_OVERLAYS_PATH = PATH / "overlays"
REMOTE_IMAGES_PATH = "config/images/"

LOGS_PATH = PATH/ "logs.txt"

REQUEST_TIMEOUT = 60


