import os
import json
import locale
import datetime

from constants import *
from webcam.utils import log, log_error, log_row
from webcam.system import System
from webcam.configuration import Configuration
from webcam.server import Server
from webcam.camera import Camera
from webcam.errors import ServerError


def main():
    """
    Main script coordinating all operations.
    """
    log_row()
    log("Start")

    try:
        # Initial values
        start = datetime.datetime.now()
        upload_logs = True
        errors_were_raised = False
        initial_configuration = None

        # Setup locale
        locale.setlocale(locale.LC_ALL, 'it_IT.utf8')

        system = System()
        status = system.report_general_status()  # TODO this can check if it's online and switch
                                                 #  to offline mode if not (issue #7)
        log("Status report:")
        for key, value in status.items():
            log(f" - {key}: {value}")

        # Load current configuration
        try:
            initial_configuration = Configuration()
        except Exception as e:
            upload_logs = False
            errors_were_raised = True
            log_error(f"Failed to load the initial configuration from {CONFIGURATION_FILE}", 
                      e, fatal="cannot proceed without any data. Exiting.")
            return

        # Verify if we're into the active hours or not, if defined
        try:
            if not initial_configuration.is_active_hours():
                log("The current time is outside working hours. Turning off.")
                upload_logs = False
                return
        except Exception as e:
            log_error("An error occurred trying to assess if the current time is within active hours. " +
                      "Assuming YES.", e)
        log("The current time is inside active hours. Proceeding.")

        # Getting the new configuration from the server
        initial_server = Server(initial_configuration)

        try:
            configuration = initial_server.update_configuration(initial_configuration)
        except Exception as e:
            log_error("Something went wrong fetching the new configuration file "
                      "from the server.", e)
            log("Falling back to the old configuration.")
            errors_were_raised = True
            configuration = initial_configuration

        log(f"Configuration in use:\n{configuration}")
        
        # Recreate the server from the new configuration
        server = Server(configuration)

        # Update the system to conform to the new configuration file
        try:
            system.apply_system_settings(configuration)

        except Exception as e:
            errors_were_raised = True
            log_error("Something happened while applying the system "
                "settings from the new configuration file.", e)
            
            log_row(char="+")
            try:
                log("Re-applying the old system configuration.")
                system.apply_system_settings(initial_configuration)
            except Exception as e:
                log_error("Something unexpected occurred while re-applying the "
                    "old system settings!", e,
                    fatal="the webcam might be in an inconsistent state." +
                    "ZANZOCAM might need manual intervention at this point.")
            log_row(char="+")

        # Create the picture
        try:
            camera = Camera(configuration)
            camera.take_picture()

        except Exception as e:
            # Try again using the old config file
            errors_were_raised = True
            log_error("An error occurred while taking the picture.", e)
            log("Trying again with the old configuration.")

            try:
                log_row(char="+")
                camera = Camera(initial_configuration)
                camera.take_picture()
                log_row(char="+")

            except Exception as ee:
                # That's the second run that failed: give up.
                errors_were_raised = True
                log_error("Something happened while running with the old configuration file too!", ee,
                            fatal="Exiting.")
                return
            
        # Send the picture
        try:
            server.upload_picture(camera.processed_image_path, camera.name, camera.extension)
        except Exception as e:
            errors_were_raised = True
            log_error("Something happened uploading the picture! It was "+
                      "probably not sent", e,
                      fatal="The error was unexpected, can't fix. The picture won't be uploaded.")
            return

    # Catch server errors: they block communication, so they are fatal anyway
    except ServerError as se:
        errors_were_raised = True
        log_error("An error occurred communicating with the server.", 
                  se, fatal="Exiting.")
        
    # Catch unexpected fatal errors
    except Exception as e:
        errors_were_raised = True
        log_error("Something unexpected occurred while running the main procedure.", 
                  e, fatal="Exiting.")
        
    # Print the completion time anyway - this block is called even after a return!
    finally:
        
        try:
            log("Cleaning up image files")
            os.remove(camera.temp_photo_path)
            os.remove(server.final_image_path)
            log("Cleanup complete")
        except Exception as e:
            errors_were_raised = True
            log_error(f"Failed to clean up image files.", e)
            log("WARNING: The filesystem might fill up if the old pictures "
                "are not removed, which can cause ZANZOCAM to fail.")

        # If we had trouble with the new config, restore the old from the backup
        # TODO assess the situation better! Maybe the failure is unrelated.
        errors_were_raised_str = "successfully"
        if errors_were_raised:
            if initial_configuration:
                initial_configuration.restore_backup()
            errors_were_raised_str = "with errors"
            
        end = datetime.datetime.now()
        log(f"Execution completed {errors_were_raised_str} in: {end - start}")
        log_row()

        # Upload the logs
        try:
            if upload_logs:
                if errors_were_raised and configuration and initial_configuration and initial_server:
                    initial_server.upload_failure_report(configuration.server, initial_configuration.server)
                else:
                    if not configuration:
                        configuration = Configuration()
                    if not server:
                        server = Server(configuration)            
                    server.upload_logs()
                
        except Exception as e:
            log_error("Something happened uploading the logs:", e, fatal="Logs won't be uploaded.")




if "__main__" == __name__:
    main()

