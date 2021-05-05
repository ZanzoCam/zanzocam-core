import os
import sys
import json
import locale
import logging
import datetime
import subprocess
from time import sleep

import constants
from constants import *
from webcam.system import System
from webcam.configuration import Configuration
from webcam.server import Server
from webcam.camera import Camera
from webcam.errors import ServerError
from webcam.utils import log, log_error, log_row



def main():
    """
    Main script coordinating all operations.

    Remember: catch all that is not essential and log it loudly,
    let everything critical break and catch it at the end.
    """
    # Setup the logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        handlers=[
            logging.FileHandler(constants.CAMERA_LOG),
            logging.StreamHandler(sys.stdout),
        ]
    )
    log_row()
    log("Start")

    try:
        # Initial values
        upload_logs = True
        errors_were_raised = False
        restore_required = False
        old_config = None
        config = None
        server = None
        camera = None

        # Check the system status
        try:
            start = datetime.datetime.now()
            
            log("Status report:")
            system = System()
            status = system.report_general_status() 
            for key, value in status.items():
                log(f" - {key}: {value}")
        except Exception as e:
            log_error("Something unexpected happened during the system "
                      "status check. Skipping this step. This might be "
                      "a symptom of deeper issues, don't ignore this!", e)
            errors_were_raised = True

        # Setup locale
        try:
            locale.setlocale(locale.LC_ALL, LOCALE)
        except Exception as e:
            log_error("Could not set locale. Proceeding without it.", e)

        # Load current configuration
        try:
            old_config = Configuration()
        except Exception as e:
            upload_logs = False  # Cannot do it without any server data
            errors_were_raised = True
            log_error(f"Failed to load the initial configuration from "
                      f"'{CONFIGURATION_FILE}'.", e, 
                      fatal="cannot proceed without any data. Exiting.")
            return

        # Verify if we're into the active hours or not, if defined
        try:
            log(f"Checking if {datetime.datetime.now().strftime('%H:%M')} "
                f"is into active interval "
                f"({old_config.get_start_time()} to "
                f"{old_config.get_stop_time()}).")

            if not old_config.within_active_hours():
                upload_logs = False
                log("The current time is outside active hours. Turning off.")
                return  # The 'finally' block is run nonetheless after this

            log("The current time is inside active hours.")

        except Exception as e:
            log_error("An error occurred trying to assess if the "
                      "current time is within active hours. "
                      "Assuming YES.", e)
            errors_were_raised = True
        
        # Creating the initial server and getting the new config
        # NOTE: This is critical, so don't catch locally
        server = Server(old_config.get_server_settings())
        endpoint = server.get_endpoint()

        try:
            log(f"Downloading the new configuration file from {endpoint}")
            config = server.update_configuration(old_config)
            log("Configuration updated successfully.")

        except Exception as e:
            log_error("Something went wrong fetching the new configuration "
                      "file from the server. Keeping the old configuration.", e)
            errors_were_raised = True
            restore_required = True
            config = old_config

        finally:
            log(f"Configuration in use:\n{config}")
        
        try:
            log(f"Scanning the new configuration for overlays to download.")
            overlays_list = config.overlays_to_download()
            log(f"Overlays to download: {overlays_list}")
            
            if overlays_list:
                log(f"Downloading overlay images from '{endpoint}' "
                    f"into '{IMAGE_OVERLAYS_PATH}'")
                server.download_overlay_images(overlays_list)

        except Exception as e:
            log_error("Something went wrong fetching the new overlay "
                      "images from the server. Ignoring them.", e)
            errors_were_raised = True
            restore_required = False

        # Recreate the server from the new configuration
        server = Server(config.get_server_settings())

        # Update the system to conform to the new configuration file
        try:
            if config.get_system_settings() != old_config.get_system_settings():
                log("Applying new system settings.")
                system.apply_system_settings(config.get_system_settings())
            else:
                log("System settings didn't change: doing nothing.")

        except Exception as e:
            errors_were_raised = True
            restore_required = False
            log_error("Something happened while applying the system "
                      "settings from the new configuration file. "
                      "Most likely the system settings were not altered. "
                      "This means the system is still using this system "
                      "settings:\n" +
                      json.dumps(old_config.get_system_settings(), indent=4) +
                      "\n", e)

        # Create the picture
        try:
            camera = Camera(config)
            camera.take_picture()

        except Exception as e:
            # Try again using the old config file
            errors_were_raised = True
            log_error("An error occurred while taking the picture.", e)
            log(f"Waiting 30 seconds and then trying again.")
            sleep(30)

            try:
                log_row(char="+")
                camera = Camera(config)
                camera.take_picture()
                log_row(char="+")

            except Exception as ee:
                # That's the second run that failed: give up.
                errors_were_raised = True
                log_error("Something happened at the second attempt too!", ee,
                            fatal="Exiting.")
                return  # The 'finally' block will run after this
            
        # Send the picture
        try:
            log(f"Uploading picture to {server.get_endpoint()}")
            server.upload_picture(camera.processed_image_path, 
                                  camera.name, 
                                  camera.extension)
       
        except Exception as e:
            errors_were_raised = True
            restore_required = True
            log_error("Something happened uploading the picture! "
                      "It was probably not sent.", e,
                      fatal="The error was unexpected, can't fix. "
                            "The picture won't be uploaded.")
            return # The 'finally' block will run after this


    # Catch server errors: they block communication, so they are fatal anyway
    except ServerError as se:
        errors_were_raised = True
        # If something went wrong with the server
        # it's probably better to restore the old config.
        # If the server is not at fault, the old config
        # will point to the same server anyway  
        restore_required = True  
        log_error("An error occurred communicating with the server.", 
                  se, fatal="Restoring the old configuration file and exiting.")
        
    # Catch unexpected fatal errors
    except Exception as e:
        errors_were_raised = True

        # If something really unexpected went wrong
        # it's probably better to restore the old config.
        # If the server is not at fault, the old config
        # will point to the right server anyway  
        restore_required = True
        log_error("Something unexpected occurred running the main procedure.", 
                  e, fatal="Restoring the old configuration file and exiting.")
        
    # Print the completion time anyway - this block is called even after a return.
    finally:
        
        # Clean up image files if existing
        try:
            if camera:
                log("Cleaning up image files.")
                camera.cleanup_image_files()
            
        except Exception as e:
            errors_were_raised = True
            log_error(f"Failed to clean up image files. Note that the "
                      f"filesystem might fill up if the old pictures "
                      f"are not removed, which can cause ZANZOCAM to fail.", e)

        # If we had trouble with the new config, restore the old from the backup
        # TODO assess the situation better! Maybe the failure is unrelated.
        if restore_required and old_config:
            
            log("Restoring the old configuration file. Note that this "
                "operation affects the server settings only: system "
                "settings might be still setup according to the newly "
                "downloaded config file (if it was downloaded). Check the "
                "above logs carefully to assess the situation.")
            old_config.restore_backup()
            log("The next run will use the following server configuration:")
            old_config = Configuration()
            print(json.dumps(old_config.get_server_settings(), indent=4))

        errors_were_raised_str = "successfully"
        if errors_were_raised or restore_required:
            errors_were_raised_str = "with errors"

        end = datetime.datetime.now()
        log(f"Execution completed {errors_were_raised_str} in: {end - start}")
        log_row()

        # Upload the logs
        if upload_logs:
            try:
                endpoint = "[no server available]"
                config = Configuration()
                server = Server(config.get_server_settings()) 
                endpoint = server.get_endpoint()  

                server.upload_logs()
                log(f"Logs uploaded successfully to {endpoint}")

                # If restore was required, send a failure report to the old server
                if restore_required:
                    wrong_conf = config.get_server_settings()
                    right_conf = old_config.get_server_settings()

                    if wrong_conf != right_conf:
                        log(f"Sending failure report to "
                            f"{server.get_endpoint()}")
                        server.upload_failure_report(wrong_conf, right_conf)
                        log("Failure report uploaded successfully.")
                
                # If so required, send diagnostics to the server
                try:
                    if getattr(config, 'send_diagnostics', False):
                        system.generate_diagnostics()
                        log(f"Sending diagnostic report to {endpoint}")
                        server.upload_diagnostics()
                except Exception as ee:
                    # FIXME deal with this a bit better if we see 
                    # this logs are useful
                    log("An error occurred while sending the diagnostics. "
                        "Ignoring this.")

            except Exception as e:
                log_row("-")
                log_error(f"Something happened while uploading the logs "
                          f"to {endpoint}", e, 
                          fatal="Logs won't be uploaded.")
                log_row("-")


if "__main__" == __name__:
    main()

