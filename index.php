<?php
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
    $imagePath = "/var/www/bots/pictures/";

    if(is_uploaded_file($imagetemp)) {
        if(move_uploaded_file($imagetemp, $imagePath . $imagename)) {
            echo "OK";
        }
        else {
            echo "Failed to move your image.";
        }
    }
    else {
        echo "Failed to upload your image.";
    }
?>
