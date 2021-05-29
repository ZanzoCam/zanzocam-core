# How to re-create the image

### Create the base image and boot

This steps gives you a SD card that can connect to your WiFi network, so that you can control it through SSH. This is necessary for the later steps. You might want to delete your network information at the end of the process.

- Download latest RPI OS [here](https://downloads.raspberrypi.org/raspios_lite_armhf/images/raspios_lite_armhf-2021-03-25/2021-03-04-raspios-buster-armhf-lite.zip)
- Unzip it
- Flash onto SD:
    - `dd if=nome-immagine.img of=/dev/sdX bs=4M status=progress oflag=sync` with `sudo`
- Add empty `ssh` file in the `boot` partition
- Add `config.txt` file in the `boot` partition (if it exists already, delete it)
    - Content:
```
# Disable the rainbow splash screen
disable_splash=1

# No boot delay
boot_delay=0

# Disable the LED
dtparam=act_led_trigger=none
dtparam=act_led_activelow=on

# Enable camera
start_x=1             # essential, although a bit misleading
gpu_mem=256           # the memory allocated for the camera
disable_camera_led=1  # optional, if you don't want the led to glow

# Disable Bluetooth
dtoverlay=disable-bt
```
- Change `/etc/wpa_supplicant/wpa_supplicant.conf` on `rootfs` with your local wifi data
    - Example content:
```
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=IT

network={
    ssid="SSIDNAME"
    psk="PASSWORD"
}
```
- Boot the Pi with this SD card.
- SSH into it. Assuming your router's IP is something like 192.168.1.0 (mind the first three numbers and change them accordingly in the commands below):
    - Find its IP with `nmap -p 22 192.168.1.0/24`. In the list that appears, one of the devices should be your Raspberry Pi (find it by the name or by exclusion).
    - Connect to it with SSH using the IP just discovered: `ssh pi@192.168.1.xxx` (password is 'raspberry')


### Basic setup (libraries and configuration)

This step installs a few libraries required for the webcam to work.

- Switch from the `pi` user to `zanzocam-bot`:
    - Create user with home directory: `sudo useradd -m zanzocam-bot`
    - Change password: `sudo passwd zanzocam-bot`
    - Make sudoer: `sudo usermod -aG sudo zanzocam-bot`
    - Allow passwordless `sudo` for `zanzocam-bot`: `sudo nano /etc/sudoers`
          - Add ad the end: `zanzocam-bot ALL=(ALL:ALL) NOPASSWD:ALL`
    - Allow `zanzocam-bot` to access the webcam: `sudo usermod -aG video zanzocam-bot`

    - Leave the SSH connection and reconnect with `zanzocam-bot`
    - Lock `pi`:  `sudo passwd -l pi`
    - Kill all processes (shold be none): `sudo pkill -KILL -u pi`
    - Remove the user: `sudo deluser --remove-home pi`
    
- Generate locales:
    - Uncomment the IT locale in the proper file:  `sudo perl -pi -e 's/# it_IT.UTF-8 UTF-8/it_IT.UTF-8 UTF-8/g' /etc/locale.gen`
    - Comment the default EN locale in the proper file:  `sudo perl -pi -e 's/en_GB.UTF-8 UTF-8/# en_GB.UTF-8 UTF-8/g' /etc/locale.gen`
    - Generate locales: `sudo locale-gen it_IT.UTF-8`
    - Set locale: `sudo localectl set-locale LANG=it_IT.UTF-8`
    - Update locales: `sudo update-locale it_IT.UTF-8`

Note: this procedure might raise some Perl errors, like:
```
perl: warning: Setting locale failed.
perl: warning: Please check that your locale settings:
        LANGUAGE = (unset),
        LC_ALL = (unset),
        LC_ADDRESS = "fr_FR.UTF-8",
        LC_NAME = "fr_FR.UTF-8",
        LC_MONETARY = "fr_FR.UTF-8",
        LC_PAPER = "fr_FR.UTF-8",
        LC_IDENTIFICATION = "fr_FR.UTF-8",
        LC_TELEPHONE = "fr_FR.UTF-8",
        LC_MEASUREMENT = "fr_FR.UTF-8",
        LC_NUMERIC = "fr_FR.UTF-8",
        LANG = "en_GB.UTF-8"
    are supported and installed on your system.
perl: warning: Falling back to the standard locale ("C").
```
These are due to a directive on your local machine, in `/etc/ssh/ssh_config`: `SendEnv LANG LC_*`.
Comment it out to avoid such errors from arising on your Pi.

- Set timezone: `sudo timedatectl set-timezone Europe/Rome`
    
- Create alias for `ll` in `~/.bashrc`: `nano ~/.bashrc`
    - Add at the end: `alias ll="ls -lah"`

- Update the index: `sudo apt update`
- Install utilities, graphics libraries, fonts: `sudo apt install -y git whois libopenjp2-7-dev libtiff-dev fonts-dejavu`.
  - Note: we're installing the DejaVu font. If you want to change it, install the proper package at this stage and, at the end of the procedure, modify `constants.py` in `home/zanzocam-bot/venv/src/zanzocam/zanzocam/`. This file constains a constant called `FONT_PATH` which you should point to your font's path. 
- Setup cronjob to turn off HDMI at reboot:
    - `sudo nano /etc/cron.d/no-hdmi`
    - Content:
```
# Disable the HDMI port (to save power)
@reboot /usr/bin/tvservice -o
```
- Disable the swap (swaps tends to "burn" SD cards very fast due to the very frequent writes. Turns out the Raspberry Pi has quite enough RAM to work without swap):
  - `sudo dphys-swapfile swapoff`
  - `sudo dphys-swapfile uninstall`
  - `sudo update-rc.d dphys-swapfile remove`
  - `sudo apt purge -y dphys-swapfile`

- Install the webcam module:
    - Install pip3 and venv: `sudo apt install -y python3-pip python3-venv`
    - Create venv in the home: `cd ~ && python3 -m venv venv`
    - Activate venv: `source venv/bin/activate`
    - Install Zanzocam webcam into it: `pip install -e "git+https://github.com/ZanSara/zanzocam.git#egg=zanzocam[all]&subdirectory=zanzocam"`
    - Leave venv: `deactivate`

### Setup the autohotspot feature

This step makes the Pi able to generate its own WiFi network 
(SSID & password, see below) when no known WiFi network is detected.

Instructions found [here](https://www.raspberryconnect.com/projects/65-raspberrypi-hotspot-accesspoints/158-raspberry-pi-auto-wifi-hotspot-switch-direct-connection)

- Install `hostapd` and `dnsmasq`
    - `sudo apt install -y hostapd dnsmasq`
- `hostapd` and `dnsmasq` run when the Raspberry is started, but they should only start if the home router is not found. So automatic startup needs to be disabled and `hostapd` needs to be unmasked:
    - `sudo systemctl unmask hostapd`
    - `sudo systemctl disable hostapd`
    - `sudo systemctl disable dnsmasq`
- Edit `hostapd` configuration file to create a network called `zanzocam-setup` and password `webcamdelrifugio` (on WiFi channel 8):
    - `sudo nano /etc/hostapd/hostapd.conf`
    - Content:
```
# 2.4GHz setup wifi 80211 b,g,n
interface=wlan0
driver=nl80211
ssid=zanzocam-setup
hw_mode=g
channel=8
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=webcamdelrifugio
wpa_key_mgmt=WPA-PSK
wpa_pairwise=CCMP TKIP
rsn_pairwise=CCMP

# 80211n
country_code=IT
ieee80211n=1
ieee80211d=1
```    
- Edit `hostapd` defaults
    - `sudo nano /etc/default/hostapd`
    - Change `#DAEMON_CONF=""` into `DAEMON_CONF="/etc/hostapd/hostapd.conf"`
    - Check that `DAEMON_OPTS=""` is preceded by a `#`, so that the line reads `#DAEMON_OPTS=""`
- Edit `dnsmasq` configuration:
    - `sudo nano /etc/dnsmasq.conf`
    - Add at the bottom:
```
#AutoHotspot Config
#stop DNSmasq from using resolv.conf
no-resolv
#Interface to use
interface=wlan0
bind-interfaces
dhcp-range=10.0.0.50,10.0.0.150,12h
```
- Modify the `interfaces` file:
    - `sudo nano /etc/network/interfaces`
    - Must be equal to:
```
# interfaces(5) file used by ifup(8) and ifdown(8) 

# Please note that this file is written to be used with dhcpcd 
# For static IP, consult /etc/dhcpcd.conf and 'man dhcpcd.conf' 

# Include files from /etc/network/interfaces.d: 
source-directory /etc/network/interfaces.d 
```
- Stop `dhcpcd` from starting the wifi network, so that the `autohotspot` script in the next step can work:
    - `sudo nano /etc/dhcpcd.conf`
    - Add at the bottom: `nohook wpa_supplicant`
- Create a service which will run the autohotspot script when the Raspberry Pi starts up
    - `sudo nano /etc/systemd/system/autohotspot.service`
    - Content:
```
[Unit]
Description=Automatically generates an hotspot when a valid ssid is not in range
After=multi-user.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/autohotspot

[Install]
WantedBy=multi-user.target
```
- Enable the service:
    - `sudo systemctl enable autohotspot.service`
- Create the `autohotspot` script:
    - `sudo nano /usr/bin/autohotspot`
    - Content:
```
#!/bin/bash
#version 0.961-N/HS

#You may share this script on the condition a reference to RaspberryConnect.com 
#must be included in copies or derivatives of this script. 

#A script to switch between a wifi network and a non internet routed Hotspot
#Works at startup or with a seperate timer or manually without a reboot
#Other setup required find out more at
#http://www.raspberryconnect.com

wifidev="wlan0" #device name to use. Default is wlan0.
#use the command: iw dev ,to see wifi interface name 

IFSdef=$IFS
cnt=0
#These four lines capture the wifi networks the RPi is setup to use
wpassid=$(awk '/ssid="/{ print $0 }' /etc/wpa_supplicant/wpa_supplicant.conf | awk -F'ssid=' '{ print $2 }' | sed 's/\r//g'| awk 'BEGIN{ORS=","} {print}' | sed 's/\"/''/g' | sed 's/,$//')
IFS=","
ssids=($wpassid)
IFS=$IFSdef #reset back to defaults


#Note:If you only want to check for certain SSIDs
#Remove the # in in front of ssids=('mySSID1'.... below and put a # infront of all four lines above
# separated by a space, eg ('mySSID1' 'mySSID2')
#ssids=('mySSID1' 'mySSID2' 'mySSID3')

#Enter the Routers Mac Addresses for hidden SSIDs, seperated by spaces ie 
#( '11:22:33:44:55:66' 'aa:bb:cc:dd:ee:ff' ) 
mac=()

ssidsmac=("${ssids[@]}" "${mac[@]}") #combines ssid and MAC for checking

createAdHocNetwork()
{
    echo "Creating Hotspot"
    ip link set dev "$wifidev" down
    ip a add 10.0.0.5/24 brd + dev "$wifidev"
    ip link set dev "$wifidev" up
    dhcpcd -k "$wifidev" >/dev/null 2>&1
    systemctl start dnsmasq
    systemctl start hostapd
}

KillHotspot()
{
    echo "Shutting Down Hotspot"
    ip link set dev "$wifidev" down
    systemctl stop hostapd
    systemctl stop dnsmasq
    ip addr flush dev "$wifidev"
    ip link set dev "$wifidev" up
    dhcpcd  -n "$wifidev" >/dev/null 2>&1
}

ChkWifiUp()
{
	echo "Checking WiFi connection ok"
        sleep 20 #give time for connection to be completed to router
	if ! wpa_cli -i "$wifidev" status | grep 'ip_address' >/dev/null 2>&1
        then #Failed to connect to wifi (check your wifi settings, password etc)
	       echo 'Wifi failed to connect, falling back to Hotspot.'
               wpa_cli terminate "$wifidev" >/dev/null 2>&1
	       createAdHocNetwork
	fi
}


chksys()
{
    #After some system updates hostapd gets masked using Raspbian Buster, and above. This checks and fixes  
    #the issue and also checks dnsmasq is ok so the hotspot can be generated.
    #Check Hostapd is unmasked and disabled
    if systemctl -all list-unit-files hostapd.service | grep "hostapd.service masked" >/dev/null 2>&1 ;then
	systemctl unmask hostapd.service >/dev/null 2>&1
    fi
    if systemctl -all list-unit-files hostapd.service | grep "hostapd.service enabled" >/dev/null 2>&1 ;then
	systemctl disable hostapd.service >/dev/null 2>&1
	systemctl stop hostapd >/dev/null 2>&1
    fi
    #Check dnsmasq is disabled
    if systemctl -all list-unit-files dnsmasq.service | grep "dnsmasq.service masked" >/dev/null 2>&1 ;then
	systemctl unmask dnsmasq >/dev/null 2>&1
    fi
    if systemctl -all list-unit-files dnsmasq.service | grep "dnsmasq.service enabled" >/dev/null 2>&1 ;then
	systemctl disable dnsmasq >/dev/null 2>&1
	systemctl stop dnsmasq >/dev/null 2>&1
    fi
}


FindSSID()
{
#Check to see what SSID's and MAC addresses are in range
ssidChk=('NoSSid')
i=0; j=0
until [ $i -eq 1 ] #wait for wifi if busy, usb wifi is slower.
do
        ssidreply=$((iw dev "$wifidev" scan ap-force | egrep "^BSS|SSID:") 2>&1) >/dev/null 2>&1 
        #echo "SSid's in range: " $ssidreply
	printf '%s\n' "${ssidreply[@]}"
        echo "Device Available Check try " $j
        if (($j >= 10)); then #if busy 10 times goto hotspot
                 echo "Device busy or unavailable 10 times, going to Hotspot"
                 ssidreply=""
                 i=1
	elif echo "$ssidreply" | grep "No such device (-19)" >/dev/null 2>&1; then
                echo "No Device Reported, try " $j
		NoDevice
        elif echo "$ssidreply" | grep "Network is down (-100)" >/dev/null 2>&1 ; then
                echo "Network Not available, trying again" $j
                j=$((j + 1))
                sleep 2
	elif echo "$ssidreply" | grep "Read-only file system (-30)" >/dev/null 2>&1 ; then
		echo "Temporary Read only file system, trying again"
		j=$((j + 1))
		sleep 2
	elif echo "$ssidreply" | grep "Invalid exchange (-52)" >/dev/null 2>&1 ; then
		echo "Temporary unavailable, trying again"
		j=$((j + 1))
		sleep 2
	elif echo "$ssidreply" | grep -v "resource busy (-16)"  >/dev/null 2>&1 ; then
               echo "Device Available, checking SSid Results"
		i=1
	else #see if device not busy in 2 seconds
                echo "Device unavailable checking again, try " $j
		j=$((j + 1))
		sleep 2
	fi
done

for ssid in "${ssidsmac[@]}"
do
     if (echo "$ssidreply" | grep -F -- "$ssid") >/dev/null 2>&1
     then
	      #Valid SSid found, passing to script
              echo "Valid SSID Detected, assesing Wifi status"
              ssidChk=$ssid
              return 0
      else
	      #No Network found, NoSSid issued"
              echo "No SSid found, assessing WiFi status"
              ssidChk='NoSSid'
     fi
done
}

NoDevice()
{
	#if no wifi device,ie usb wifi removed, activate wifi so when it is
	#reconnected wifi to a router will be available
	echo "No wifi device connected"
	wpa_supplicant -B -i "$wifidev" -c /etc/wpa_supplicant/wpa_supplicant.conf >/dev/null 2>&1
	exit 1
}

chksys
FindSSID

#Create Hotspot or connect to valid wifi networks
if [ "$ssidChk" != "NoSSid" ] 
then
       if systemctl status hostapd | grep "(running)" >/dev/null 2>&1
       then #hotspot running and ssid in range
              KillHotspot
              echo "Hotspot Deactivated, Bringing Wifi Up"
              wpa_supplicant -B -i "$wifidev" -c /etc/wpa_supplicant/wpa_supplicant.conf >/dev/null 2>&1
              ChkWifiUp
       elif { wpa_cli -i "$wifidev" status | grep 'ip_address'; } >/dev/null 2>&1
       then #Already connected
              echo "Wifi already connected to a network"
       else #ssid exists and no hotspot running connect to wifi network
              echo "Connecting to the WiFi Network"
              wpa_supplicant -B -i "$wifidev" -c /etc/wpa_supplicant/wpa_supplicant.conf >/dev/null 2>&1
              ChkWifiUp
       fi
else #ssid or MAC address not in range
       if systemctl status hostapd | grep "(running)" >/dev/null 2>&1
       then
              echo "Hostspot already active"
       elif { wpa_cli status | grep "$wifidev"; } >/dev/null 2>&1
       then
              echo "Cleaning wifi files and Activating Hotspot"
              wpa_cli terminate >/dev/null 2>&1
              ip addr flush "$wifidev"
              ip link set dev "$wifidev" down
              rm -r /var/run/wpa_supplicant >/dev/null 2>&1
              createAdHocNetwork
       else #"No SSID, activating Hotspot"
              createAdHocNetwork
       fi
fi

```
- Make it executable:
    - `sudo chmod +x /usr/bin/autohotspot`
    
- Some boards actually come with rfkilled WiFi interface and wlan0 down. Therefore:
    - `sudo nano /etc/crontab` (this file can run sudo commands)
    - Append at the end of the file: `@reboot root rfkill unblock 0 && ifconfig wlan0 up && /usr/bin/autohotspot`

- To test:
    - `sudo reboot`. 
    - After reboot it should manage to connect to your home network.
    - `ssh` into it.
    - Remove your network details from `/etc/wpa_supplocant/wpa_supplicant.conf`
    - `sudo reboot`.
    - You should see a wifi network called "zanzocam-setup" that you can connect to.
    - Connect and `ssh` into the Raspberry again (IP is `10.0.0.5`)


### Prepare setup server
Once the Pi can generate its own network, we make it able to receive HTTP requests by setting up a web server: Nginx.

Instructions [here](https://www.raspberrypi.org/documentation/remote-access/web-server/nginx.md) for Nginx and [here](https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-uswgi-and-nginx-on-ubuntu-18-04) for Flask.

- Install Nginx:
    - Install it: `sudo apt install -y nginx libssl-dev libffi-dev build-essential apache2-utils`
    - Start it: `sudo /etc/init.d/nginx start`
    - Create a `.htpasswd` file in the home: `htpasswd -c /home/zanzocam-bot/.htpasswd zanzocam-user` (the image password here is `lampone`)
    - Create a systemdunit file: `sudo nano /etc/systemd/system/zanzocam-web-ui.service`. Content:
```
[Unit]
Description=uWSGI instance to serve the ZANZOCAM web UI
After=network.target

[Service]
User=zanzocam-bot
Group=www-data
WorkingDirectory=/home/zanzocam-bot/venv/src/zanzocam/zanzocam/web_ui
Environment="PATH=/home/zanzocam-bot/zanzocam/venv/bin"
ExecStart=/home/zanzocam-bot/venv/bin/uwsgi --ini web-ui.ini

[Install]
WantedBy=multi-user.target
```
- Enable the service: `sudo systemctl enable zanzocam-web-ui`
- Start the service: `sudo systemctl start zanzocam-web-ui`
- Create Nginx configuration: `sudo nano /etc/nginx/sites-available/zanzocam-web-ui`
- Content:
```
server {
    listen 80;

    auth_basic "Login";
    auth_basic_user_file /home/zanzocam-bot/.htpasswd;

    location / {
        include uwsgi_params;
        uwsgi_pass unix:/home/zanzocam-bot/venv/src/zanzocam/zanzocam/web_ui/web-ui.sock;
        uwsgi_read_timeout 600;

    }
}
```
- Enable the new config: `sudo ln -s /etc/nginx/sites-available/zanzocam-web-ui /etc/nginx/sites-enabled`
- Disable the default config: `sudo rm /etc/nginx/sites-enabled/default`
- Check for errors with `sudo nginx -t`
- Restart Nginx: `sudo systemctl restart nginx`


### Create the image

- Insert the SD card into the computer and mount it
- Resize `rootfs` to be approximately 3.5G (can be done with GParted).
- Clone the resized content of the SD into an image: `dd if=/dev/sdX of=zanzocam.img bs=4M status=progress oflag=sync` with `sudo`
- Install resizing tool: `sudo apt install -y qemu-utils`
- Shrink it to a smaller size (4GB should be safe): `sudo qemu-img resize zanzocam.img 3.8G`
    - If you're building an image to be used with the Raspberry Imager, use a multiple of 512: `4013109760B` instead of `3.8G`

The image is ready to be flashed on any SD card larger than 4GB. 
Note that the filesystem will not expand.

If you want to upload/send it, compress it first with 
`tar -czvf zanzocam.tar.gz zanzocam.img`


