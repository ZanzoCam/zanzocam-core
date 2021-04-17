<?php
header('Content-Type: application/json');

$image_path = "pictures/";
$logs_path = "logs/";
$config_path = "configuration/";
$config_file = "configuration/configuration.json";
$backup_config_file = "configuration/backup/configuration_".date('Y-m-d_H:i:s').".json";
$config_images_path = "configuration/overlays/";


// If it's not a POST, return the config file and the images index
if (empty($_POST) == 1 && empty($_FILES) == 1) {
    $config_string = file_get_contents($config_file);
    $config = json_decode($config_string);
    $overlays_list = glob($config_images_path.'*');
    $response = array("configuration" => $config, "overlays_list" => $overlays_list);
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
    
    // Logs are being uploaded - store them
    if ($logs){
        if (file_put_contents($logs_path."logs_".date('Y-m-d_H:i:s').".txt", $logs)){
            $response["logs"] = "";
        } else {
            $response["logs"] = "Failed to save the logs on the server.";
        }
    }

    // A photo is being uploaded - store it and if needed delete/rename the others
    if ($imagename){
        if(is_uploaded_file($imagetemp)) {
            
            // Check what the config file contains with respect to pictures storage
            $configurationFileAsString = file_get_contents($config_file);
            $configurationFile = json_decode($configurationFileAsString, true);
            
            if (isset($configurationFile["server"]["max_photos"])){
            
                $maxPhotos = intval($configurationFile["server"]["max_photos"]);
                
                // If a maximum number of photos ia allowed, add a prefix to the current photo
                if($maxPhotos > 1){
                    $split_name = explode(".", $imagename);
                    $imagename = $split_name[0]."__0.".$split_name[1];
            
                    // Delete the oldest pictures if there are more than maxPhotos pictures
                    $pictures = glob($image_path."*.{jpg,png,gif}", GLOB_BRACE);
                    natsort($pictures);    // To ensure correct ordering of numbered names
                    $pictures = array_reverse($pictures);  // To allow the rename to work properly!
                    
                    // Rename the other pictures
                    foreach ($pictures as $old_name){

                        $no_extension_name = explode(".", $old_name);
                        $exploded_name = explode("__", $no_extension_name[0]);

                        if (count($exploded_name) == 2 && is_numeric($exploded_name[1])) {
                            $name = $exploded_name[0];
                            $position = $exploded_name[1] + 1;
                            $extension = $no_extension_name[1];

                            if($position > $maxPhotos){
                                unlink($old_name);
                            } else {
                                rename($old_name, $name."__".$position.".".$extension);
                            }
                        }
                    }
                }
            }
            // Finally save the new picture 
            if(move_uploaded_file($imagetemp, $image_path.$imagename)) {
                $response["photo"] = "";
            } else {
                $response["photo"] = "Failed to store the picture.";
            }
        } else {
            $response["photo"] = "Failed to upload the picture.";
        }
    }

    // A configuration file is being saved
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
        foreach($_FILES as $image){
            if(is_uploaded_file($image['tmp_name'])) {
                if(move_uploaded_file($image['tmp_name'], $config_images_path.$image['name'])) {
                    $config_images_feedback .= $image['name']." uploaded - ";
                } else {
                    $config_images_feedback .= $image['name']." failed to store - ";
                }
            } else {
                $config_images_feedback .= $image['name']." failed to upload - ";
            }
            $response["config-images"] = $config_images_feedback;
        }
    }
    echo json_encode($response)."\n";
}
?>
