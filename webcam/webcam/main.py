import os
import datetime

from webcam.constants import *
from webcam.utils import log, log_error
from webcam.system import System
from webcam.configuration import Configuration
from webcam.server import Server
from webcam.camera import Camera


def main():
    """
    Main script coordinating all operations.
    """
    print("\n==========================================\n")
    log("Start")

    # Initial setup
    start = datetime.datetime.now()
    new_configuration_raised_exception = False

    system = System()
    status = system.report_general_status()  # TODO this can check if it's online and switch
                                             #  to offline mode if not (issue #7)
    log("Status report:")
    for key, value in status.items():
        log(f" - {key}: {value}")

    try:
        old_configuration = Configuration()
    except Exception as e:
        log_error(f"Failed to load the initial configuration from {CONFIGURATION_PATH}", 
                  e, fatal="cannot proceed without any data. Exiting.")
        return

    server = Server(**old_configuration.server)

    # Getting the new configuration from the server
    try:
        configuration = server.update_configuration(old_configuration)

    except Exception as e:
        log_error("Something went wrong fetching the new configuration file "
                  "from the server.", e)
        log("Falling back to the old configuration.")
        new_configuration_raised_exception = True
        configuration = old_configuration

    log("Configuration in use:")
    print(configuration)

    # Re-initialize the server
    server = Server(**configuration.server)

    # Send logs of the previous run
    server.upload_logs()

    # Update the system to conform to the new configuration file
    try:
        system.apply_system_settings(configuration)
    except Exception as e:
        log_error("Something happened while applying the system "
            "settings from the new configuration file.", e)
        new_configuration_raised_exception = True
        log("Re-applying the old system configuration.")
        log("+++++++++++++++++++++++++++++++++++++++++++")
        try:
            system.apply_system_settings(old_configuration)
        except Exception as e:
            log_error("Something unexpected occurred while re-applying the "
                "old system settings!", e,
                fatal="the webcam might be in an inconsistent state." +
                "ZANZOCAM might need manual intervention at this point.")
        log("+++++++++++++++++++++++++++++++++++++++++++")

    # Create the picture
    try:
        camera = Camera(configuration)
        camera.take_picture()

    except Exception as e:
        # Try again using the old config file
        log_error("An error occurred while taking the picture.", e)
        new_configuration_raised_exception = True
        log("Trying again with the old configuration.")
        log("+++++++++++++++++++++++++++++++++++++++++++")
        camera = Camera(old_configuration)
        camera.take_picture()
        log("+++++++++++++++++++++++++++++++++++++++++++")
        return

        # That's the second run that failed: give up.
        log_error("Something happened while running with the old configuration file too!", e,
                    fatal="exiting.")
        return

    # Send the picture
    if os.path.exists(PATH / camera.processed_image_name):
        server.upload_picture(PATH / camera.processed_image_name)
        camera.clean_up()

    # If we had trouble with the new config, restore the old from the backup
    # TODO assess the situation better! Maybe the failure is unrelated.
    errors_were_raised = "successfully"
    if new_configuration_raised_exception:
        old_configuration.restore_backup()
        errors_were_raised = "with errors"

    end = datetime.datetime.now()
    log(f"Execution completed {errors_were_raised} in: {end - start}")
    print("\n==========================================\n")




if "__main__" == __name__:
    main()

