<?php
    $logs = $_POST['logs'];
    $image = $_POST['photo'];
    //Stores the filename as it was on the client computer.
    $imagename = $_FILES['photo']['name'];
    //Stores the filetype e.g image/jpeg
    $imagetype = $_FILES['photo']['type'];
    //Stores any error codes from the upload.
    $imageerror = $_FILES['photo']['error'];
    //Stores the tempname as it is given by the host when uploaded.
    $imagetemp = $_FILES['photo']['tmp_name'];

    //The path you wish to upload the image to
    $image_path = "/var/www/bots/pictures/";
    $logs_path = "/var/www/bots/logs/";
    $config_path = "/var/www/bots/config/configuration.json";

    file_put_contents($logs_path."logs".date('Y-m-d_H:i:s').".txt");

    if(is_uploaded_file($imagetemp)) {
        if(move_uploaded_file($imagetemp, $image_path . $imagename)) {
            readfile($config_path);
        }
        else {
            echo "STORING FAILED";
        }
    }
    else {
        echo "UPLOAD FAILED";
    }
?>
