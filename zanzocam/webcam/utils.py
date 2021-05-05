import sys
import json
import logging
import datetime
import traceback
import constants
from webcam.errors import UnexpectedServerResponse


class AllStringEncoder(json.JSONEncoder):
    """
    To transform every value into a string
    """
    def default(self, o):
        return str(o)


def log(msg: str) -> None:
    """ 
    Logs the message to the console
    """
    logging.info(f"{datetime.datetime.now()} -> {msg}")


def log_error(msg: str, e: Exception=None, fatal: str=None) -> None:
    """
    Logs an error to the console
    """
    fatal_msg = ""
    if fatal is not None:
        fatal_msg = f"THIS ERROR IS FATAL: {fatal}"

    stacktrace = ""
    if e is not None:
        stacktrace += f"The exception is:\n\n{traceback.format_exc()}\n"

    log(f"ERROR! {msg} {fatal_msg} {stacktrace}")
    
    

def log_row(char: str = "=") -> None:
    """ 
    Logs a row to the console
    """
    logging.info(f"\n{char*50}\n")
