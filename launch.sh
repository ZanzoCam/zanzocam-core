sudo apt-get install p7zip git python3-pip python3-tk sshpass whois
pip3 install tk requests ansible ansible-runner
ansible-galaxy collection install community.general
python3 ./files/setup/setup.py
