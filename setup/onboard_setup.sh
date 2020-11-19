
# Forces the user to setup the password at the first login
sudo passwd --expire pi

# Install system packages and Python packages
sudo apt-get -y install python3-pip libopenjp2-7-dev libtiff-dev fonts-dejavu
pip3 install Pillow picamera

sudo chown pi:pi webcam

# Installa il cronjob
crontab -l > .temp-cronjob
echo "*/5 * * * * python3 /home/pi/webcam/camera.py > /home/pi/logs.txt 2>&1" >> .temp-cronjob
crontab .temp-cronjob
rm .temp-cronjob


