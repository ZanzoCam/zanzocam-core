<?php
header('Content-Type: application/json');

$image_path = "pictures/";
$logs_path = "logs/";
$config_path = "config/configuration.json";

// If it's not a POST, return the config file
if (empty($_POST) == 1 && empty($_FILES) == 1) {
    $config_string = file_get_contents($config_path);
    $config = json_decode($config_string);
    $response = array("configuration" => $config);
    echo json_encode($response);

// If it's a POST, store picture and logs
} else {
    $response = array(
        "photo" => "Photo not detected",
        "logs" => "Logs not detected",
    );
    $logs = $_POST['logs'];

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
    echo json_encode($response)."\n";
}
?>

