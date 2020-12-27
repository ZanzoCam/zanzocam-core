import datetime
import traceback


def log(msg: str) -> None:
    """ 
    Logs the message to the console
    """
    print(f"{datetime.datetime.now()} -> {msg}")


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

