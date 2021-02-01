<?php
header('Content-Type: application/json');

$image_path = "pictures/";
$logs_path = "logs/";
$config_path = "configuration/";
$config_file = "configuration/configuration.json";
$backup_config_file = "configuration/backup/configuration_".date('Y-m-d_H:i:s').".json";
$config_images_path = "configuration/overlays/";
//$config_images_index = "pannello/config/config_images";

// If it's not a POST, return the config file and the images index
if (empty($_POST) == 1 && empty($_FILES) == 1) {
    $config_string = file_get_contents($config_file);
    //$config_images_string = file_get_contents($config_images_index);
    $config = json_decode($config_string);
    //$config_images = array_filter(explode("\n", $config_images_string));
    $response = array("configuration" => $config); //, "images" => $config_images);
    echo json_encode($response);

// If it's a POST, store picture or logs or new config with images
} else {
    $response = array(
        "config" => "Config not detected",
        "config-bak" => "Config backup not done",
        "config-images" => "Config images not detected",
        "photo" => "Photo not detected",
        "logs" => "Logs not detected",
    );
    $logs = $_POST['logs'];
    $config = $_POST['config'];
    $imagename = $_FILES['photo']['name'];
    $imagetype = $_FILES['photo']['type'];
    $imageerror = $_FILES['photo']['error'];
    $imagetemp = $_FILES['photo']['tmp_name'];

    if ($logs){
        if (file_put_contents($logs_path."logs_".date('Y-m-d_H:i:s').".txt", $logs)){
            $response["logs"] = "";
        } else {
            $response["logs"] = "Failed to save the logs on the server.";
        }
    }
    if ($imagename){
        if(is_uploaded_file($imagetemp)) {
            if(move_uploaded_file($imagetemp, $image_path.$imagename)) {
                $response["photo"] = "";
            } else {
                $response["photo"] = "Failed to store the picture.";
            }
        } else {
            $response["photo"] = "Failed to upload the picture.";
        }
    }
    if ($config){
        // Store the config JSON
        if (file_put_contents($config_file, $config)){
            $response["config"] = "";
        } else {
            $response["config"] = "Failed to save the new config on the server.";
        }
        // Store a backup with a date
        if (file_put_contents($backup_config_file, $config)){
            $response["config-bak"] = "";
        } else {
            $response["config-bak"] = "Failed to backup the new config on the server.";
        }
        // Store eventual images uploaded
        $config_images_feedback = "";
        //$config_images_index_file = fopen($config_images_index, "w");
        foreach($_FILES as $image){
            if(is_uploaded_file($image['tmp_name'])) {
                if(move_uploaded_file($image['tmp_name'], $config_images_path.$image['name'])) {
                    $config_images_feedback .= $image['name']." uploaded - ";
                    // Write the name to the index
                    //fwrite($config_images_index_file, $image['name']."\n");
                } else {
                    $config_images_feedback .= $image['name']." failed to store - ";
                }
            } else {
                $config_images_feedback .= $image['name']." failed to upload - ";
            }
            $response["config-images"] = $config_images_feedback;
        }
        //fclose($config_images_index_file);
    }
    echo json_encode($response)."\n";
}
?>

