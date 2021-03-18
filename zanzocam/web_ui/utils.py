from typing import Dict, Callable

import json
import logging
from textwrap import dedent
from flask import send_from_directory



def clear_logs(logs_path: Path):
    """
    Wipes a log file.
    """
    with open(logs_path, 'w') as d:
        pass


def _read_data_file(path: Path, default: str, action: Callable, catch_errors: bool=True):
    """ 
    Reads the given file, applies the action lambda and returns the result.
    Returns the given default value in case of errors, or lets the error 
    go through if catch_errors=False
    """
    try:
        with open(path, 'r') as d:
            return action(d)
    except Exception as e:
        if catch_errors:
            logging.error(e)
            return default
        raise e


def read_setup_data_file(path: Path, catch_errors: bool=True) -> Dict:
    """ 
    Reads the relative JSON file and returns its value as a dict.
    Returns an empty dict in case of errors, or lets the error 
    go through if catch_errors=False
    """
    return _read_data_file(path, default={}, action=lambda d: json.load(d), catch_errors=catch_errors)


def read_log_file(path: Path):
    """
    Reads a log file and returns a single block of text
    """
    return _read_data_file(path, default="", action=lambda d: "".join(d.readlines()), catch_errors=False)


def read_flag_file(path: Path, default: str, catch_errors: bool=True) -> str:
    """ 
    Reads the relative one-line file and returns its value as a string.
    Can be given a default to return in case of errors, or lets the error 
    go through if catch_errors=False
    """
    return _read_data_file(path, default=default, action=lambda d: d.read().strip(), catch_errors=catch_errors)


def read_dataset_file(path: Path, catch_errors: bool = True) -> List[str]:
    """
    Reads a multiline file and returns a list with the lines.
    Returns an empty list in case of errors, or lets the error 
    go through if catch_errors=False
    """
    return _read_data_file(path, default=[], action=lambda d: list(d.readlines()), catch_errors=catch_errors)



def write_json_file(path: Path, content):
    with open(path, "w") as f:
        json.dump(path, f, indent=4)


def write_text_file(path: Path, content):
    with open(path, "w") as f:
        f.writelines(dedent(content))


def write_flag(path: Path, content):
    with open(path, "w") as f:
        f.write(content)


def toggle_flag(flag: Path, value: str) -> int:
    """ 
    Toggle the given flag on either ON or OFF.
    Returns the statuscode to return to the sender
    """
    if value in ["ON", "OFF"]:
        try:
            write_flag(flag, value)
            return 200
        except Exception:
            return 500
    return 404

def send_from_path(path: Path):
    """
    Same as Flask's send_from_directory(), but accepts a full path
    """
    path_parts = path.split("/")
    dir = "/".join(path_parts[:-1])
    name = path_parts[-1]
    return send_from_directory(dir, name)  
    
