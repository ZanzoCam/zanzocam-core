# pylint: disable

import os
import sys
import json
import shutil
import logging
import datetime
from time import sleep

from zanzocam.constants import (
    CAMERA_LOGS,
    LOG_NAME_FORMAT,
    SEND_LOGS_FLAG,
    CAMERA_LOG,
    WAIT_AFTER_CAMERA_FAIL
)
from zanzocam.webcam import system
from zanzocam.webcam import configuration
from zanzocam.webcam.server import Server
from zanzocam.webcam.camera import Camera
from zanzocam.webcam.errors import ServerError
from zanzocam.webcam.utils import log, log_error, log_row, read_flag_file


def main():
    """
    Main script coordinating all operations.
    """
    # Setup the logging
    if not os.path.isdir(CAMERA_LOGS):
        os.mkdir(CAMERA_LOGS)
    with open(CAMERA_LOG, "w") as _:
        pass
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        handlers=[
            logging.FileHandler(CAMERA_LOG),
            logging.StreamHandler(sys.stdout),
        ]
    )
    log_row()
    log(f"Starting at {datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")

    upload_logs = read_flag_file(SEND_LOGS_FLAG)
    restore_required = False
    no_errors = True
    config = None
    server = None
    camera = None

    try:
        start = datetime.datetime.now()

        # System check
        no_errors = system.log_general_status()
 
        # Locale setup
        no_errors = system.set_locale()
 
        # Load the configuration from disk
        config = configuration.load_configuration_from_disk()
        if not config:
            log_error("", fatal="cannot proceed without any data. Exiting.")
            no_errors = False
            upload_logs = False
            return

        # Make sure configuration and system status match
        no_errors = system.apply_system_settings(config.get_system_settings())

        # Check active time
        is_active_time = config.within_active_hours()
        if is_active_time is False:
            log("Turning off.")
            return
        if is_active_time is None:  # In case of errors
            log_error("Continuing the run.")
            no_errors = True

        # Create the server
        server = Server(config.get_server_settings())

        # Update the configuration file
        new_config = server.update_configuration(config)
        if new_config:
        
            # Update the system to conform to the new configuration file
            no_errors = system.apply_system_settings(new_config.get_system_settings())
            config = new_config

        log(f"Configuration in use:\n{config}")

        # Recreate the server (might differ in the new configuration)
        server = Server(config.get_server_settings())

        # Download the overlays
        overlays_list = config.list_overlays()
        no_errors = server.download_overlay_images(overlays_list)

        # Take the picture
        for _ in range(3):
            log("Initializing camera...")
            try:
                camera = Camera(config.get_camera_settings())
                camera.take_picture()
                break

            except Exception as exception:
                log_error("An exception occurred!", exception)
                log(f"Waiting for {WAIT_AFTER_CAMERA_FAIL} sec. "
                    "and retrying...")
                sleep(WAIT_AFTER_CAMERA_FAIL)

        if not camera:
            no_errors = False
            return

        # Send the picture
        no_errors = server.upload_picture(camera.processed_image_path,
                                          camera.name,
                                          camera.extension)

        # Cleanup the image files
        no_errors = camera.cleanup_image_files()


    # Catch server errors: they block communication, so they are fatal anyway
    except Exception as exception:
        no_errors = False

        if isinstance(exception, ServerError):
            log_error("An error occurred communicating with the server.",
                      exception, fatal="Restoring the old configuration and exiting.")
        else:
            log_error("Something unexpected occurred running the main procedure.",
                      exception, fatal="Restoring the old configuration and exiting.")

        log("Restoring the old configuration file.")
        log("Note that this operation affects the server settings only: "
            "system settings might have updated properly.")
        log("Check the above logs carefully to assess the situation.")
 
        if config:
            try:
                config.restore_backup()
                old_config = configuration.load_configuration_from_disk()
                server_config = json.dumps(old_config.get_server_settings(), indent=4)
                log(f"The next run will use the following server "
                    f"configuration:\n{server_config}")

            except Exception as config_exception:
                log_error("Failed to restore the backup config. "
                          "ZanzoCam might have no valid config file for the next run.", 
                          config_exception)

    # This block is called even after a return
    finally:

        errors_str = "successfully"
        if (not no_errors) or restore_required:
            errors_str = "with errors"

        end = datetime.datetime.now()
        log(f"Execution completed {errors_str} in: {end - start}")
        log_row()

        # Store the logs
        shutil.copy2(CAMERA_LOG, CAMERA_LOGS / datetime.datetime.now().strftime(LOG_NAME_FORMAT))

        # Upload the logs
        if upload_logs:
            try:
                log("Uploading the logs...")
                current_conf = configuration.load_configuration_from_disk(quiet=True)
                server = Server(current_conf.get_server_settings())
                server.upload_logs()
            except Exception as log_exception:
                log_error("Something went wrong uploading the logs. "
                          "Logs won't be uploaded.", log_exception)
        else:
            log("Logs are not sent to the server.")


if "__main__" == __name__:
    main()
