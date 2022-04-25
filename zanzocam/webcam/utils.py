import sys
import json
import logging
import datetime
import traceback
from time import sleep
from pathlib import Path
from functools import wraps


def retry(times: int, wait_for: float):
    """
    Makes the decorated function try to run without
    exceptions 'times' times.
    If an exception occurs, logs it and tries again
    after `wait_for` seconds.
    Otherwise returns at the first successful attempt.

    Returns None in case there is an exception at the 
    last run as well.
    """
    def retry_decorator(func):
        @wraps(func)
        def retry_wrapper(*args, **kwargs) -> None:

            for i in range(times):
                try:
                    return func(*args, **kwargs)

                except Exception as e:
                    log_error("An exception occurred!", e)
                    log(f"Waiting for {wait_for} sec. "
                        "and retrying...")
                    sleep(wait_for)

            return None
        return retry_wrapper
    return retry_decorator


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
    logging.info(f"{datetime.datetime.now().strftime('%H:%M:%S')} -> {msg}")


def log_error(msg: str, e: Exception=None, fatal: str=None) -> None:
    """
    Logs an error to the console
    """
    if msg and msg != "":
        msg = f"ERROR! {msg} "
    
    fatal_msg = ""
    if fatal is not None:
        fatal_msg = f"THIS ERROR IS FATAL: {fatal}"

    stacktrace = ""
    if e is not None:
        stacktrace += f"The exception is:\n\n{traceback.format_exc()}\n"

    log(f"{msg}{fatal_msg} {stacktrace}")    
    

def log_row(char: str = "=") -> None:
    """ 
    Logs a row to the console
    """
    logging.info(f"\n{char*50}\n")


def read_flag_file(path: Path):
    """ 
    Reads the value of a flag file (text file containing either 'YES' or 'NO')
    """
    try:
        with open(path, 'r') as d:
            value = d.read()
            if value.strip().upper() == "YES":
                return True
            else:
                return False
    except Exception as e:
        logging.error(e)
        return True
