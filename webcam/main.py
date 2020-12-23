import os
import datetime

from .constants import *
from .utils import log, log_error
from .system import System
from .configuration import Configuration
from .server import Server
from .camera import Camera


def main():
    """
    Main script coordinating all operations.
    """
    log("Start")

    # Initial setup
    start = datetime.datetime.now()
    new_configuration_raised_exception_at = []

    system = System()
    status = system.collect_stats()  # TODO this can check if it's online and switch
                                     #  to offline mode if not (issue #7)
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
    if os.path.exists(camera.image_path):
        server.upload_picture(camera.image_path)
        camera.clean_up()
            
    end = datetime.datetime.now()
    log("Execution completed successfully in: {end - start}")
    print("\n==========================================\n")




if "__main__" == __name__:
    main()

