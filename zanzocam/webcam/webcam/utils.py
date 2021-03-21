import sys
import logging
import datetime
import traceback
import constants


# Setup the logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.FileHandler(constants.CAMERA_LOGS),
        logging.StreamHandler(sys.stdout),
    ]
)


def log(msg: str) -> None:
    """ 
    Logs the message to the console
    """
    logging.info(f"{datetime.datetime.now()} -> {msg}")


def log_error(msg: str, e: Exception=None, fatal: str=None) -> None:
    """
    Logs an error to the console
    """
    log(f"ERROR! {msg}")
    if e is not None:
        log(f"The exception is: " + str(e))
    traceback.print_exc()
    if fatal is not None:
        log(f"THIS ERROR IS FATAL: {fatal}")

