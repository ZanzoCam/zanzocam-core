
# Install system packages and Python packages
sudo apt-get -y install python3-pip libopenjp2-7-dev libtiff-dev
pip3 install Pillow picamera

# Installa il cronjob
crontab -l > .temp-cronjob
echo "*/5 * * * * python3 /home/pi/webcam/camera.py > /home/pi/logs.txt 2>&1" >> .temp-cronjob
crontab .temp-cronjob
rm .temp-cronjob


