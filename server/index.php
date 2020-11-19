<?php
    $image = $_POST['photo'];
    $loag = $_POST['logs'];
    //Stores the filename as it was on the client computer.
    $imagename = $_FILES['photo']['name'];
    $logsname = $_FILES['logs']['name'];
    //Stores the filetype e.g image/jpeg
    $imagetype = $_FILES['photo']['type'];
    $logstype = $_FILES['logs']['type'];
    //Stores any error codes from the upload.
    $imageerror = $_FILES['photo']['error'];
    $logserror = $_FILES['logs']['error'];
    //Stores the tempname as it is given by the host when uploaded.
    $imagetemp = $_FILES['photo']['tmp_name'];
    $logstemp = $_FILES['logs']['tmp_name'];

    //The path you wish to upload the image to
    $imagePath = "/var/www/bots/pictures/";
    $logsPath = "/var/www/bots/logs/";
    $configPath = "/var/www/bots/config/configuration.json";
    
    if(is_uploaded_file($imagetemp) && is_uploaded_file($logstemp)) {
        if(move_uploaded_file($imagetemp, $imagePath . $imagename) &&
            move_uploaded_file($logstemp, $logsPath . $logsname)) {
            
            readfile($configPath);
        }
        else {
            echo "Failed to move your image or your logs.";
        }
    }
    else {
        echo "Failed to upload your image or your logs.";
    }
?>
