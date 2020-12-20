# sudo apt-get install python3-pip python3-tk
# pip3 install tk requests

import io
import os
import re
import sys
import math
import time
import crypt
import shutil
import string
import random
import requests
import threading
import subprocess
import ansible_runner
from pathlib import Path
from functools import partial
from threading import Event, Thread
from ansible_runner.interface import init_runner


import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont 
from tkinter import scrolledtext


class Wizard:

    def __init__(self):
        """ Create the root self.window and the title, then go to the first self.window """
        
        self.ssid = None
        self.password = None
        self.server = None
        self.server_username = None
        self.server_password = None
        self.rpi_username = None
        self.rpi_password = None
        self.device = None
    
        self.window = tk.Tk()
        self.window.title("Setup ZANZOCAM")
        self.window.option_add('*Font', '18')
        
        self.window.columnconfigure(0, weight=1)
        self.window.columnconfigure(1, weight=1)
        self.window.rowconfigure(10, weight=1)
        self.window.geometry("600x700")
        
        title = tk.Label(self.window, text="Setup ZANZOCAM")
        title.grid(row=0, columnspan=2, padx=20, pady=20, sticky=tk.W + tk.E + tk.N + tk.S)
        title.config(font=(None, 22))

        self.input_window()
        self.window.mainloop()
        
    def clean_window(self):
        """ Removes all the items from the window apart from the title """
        for item in self.window.grid_slaves():
            if int(item.grid_info()["row"]) > 0:
                item.grid_forget()

    def input_window(self):
        """ Initial self.window that gathers the requirements. """
        
        ssid_label = tk.Label(self.window, text="WiFi SSID")
        ssid_label.grid(row=1, column=0, padx=20, pady=10, sticky=tk.W)
        ssid = tk.Entry(self.window)
        ssid.grid(row=1, column=1, padx=20, pady=10, sticky=tk.E)

        password_label = tk.Label(self.window, text="WiFi Password")
        password_label.grid(row=2, column=0, padx=20, pady=10, sticky=tk.W)
        password = tk.Entry(self.window)
        password.grid(row=2, column=1, padx=20, pady=10, sticky=tk.E)

        server_label = tk.Label(self.window, text="Server URL")
        server_label.grid(row=3, column=0, padx=20, pady=10, sticky=tk.W)
        server = tk.Entry(self.window)
        server.grid(row=3, column=1, padx=20, pady=10, sticky=tk.E)
        
        username_label = tk.Label(self.window, text="Server Username")
        username_label.grid(row=4, column=0, padx=20, pady=10, sticky=tk.W)
        username = tk.Entry(self.window)
        username.grid(row=4, column=1, padx=20, pady=10, sticky=tk.E)
        
        server_password_label = tk.Label(self.window, text="Server Password")
        server_password_label.grid(row=5, column=0, padx=20, pady=10, sticky=tk.W)
        server_password = tk.Entry(self.window)
        server_password.grid(row=5, column=1, padx=20, pady=10, sticky=tk.E)
        
        rpi_username_label = tk.Label(self.window, text="Nuovo Username per Raspberry PI")
        rpi_username_label.grid(row=6, column=0, padx=20, pady=10, sticky=tk.W)
        rpi_username = tk.Entry(self.window)
        rpi_username.grid(row=6, column=1, padx=20, pady=10, sticky=tk.E)
        
        rpi_password_label = tk.Label(self.window, text="Nuova Password per Raspberry PI")
        rpi_password_label.grid(row=7, column=0, padx=20, pady=10, sticky=tk.W)
        rpi_password = tk.Entry(self.window)
        rpi_password.grid(row=7, column=1, padx=20, pady=10, sticky=tk.E)

        device_label = tk.Label(self.window, text="Posizione SD (/dev/sdX)")
        device_label.grid(row=8, column=0, padx=20, pady=10, sticky=tk.W)
        device = tk.Entry(self.window)
        device.grid(row=8, column=1, padx=20, pady=10, sticky=tk.E)
        
        feedback = tk.Label(self.window, text="", fg="red")
        feedback.grid(row=9, columnspan=2, padx=10, pady=10, sticky=tk.W + tk.E + tk.N + tk.S)
        
        def proceed():
            """ Validates the input and cleans up the root self.window """
            
            self.ssid = ssid.get().strip()
            self.password = password.get().strip()
            self.server = server.get().strip()
            self.server_username = username.get().strip()
            self.server_password = server_password.get().strip()
            self.rpi_username = rpi_username.get().strip()
            self.rpi_password = rpi_password.get().strip()
            self.device = device.get().strip()
            
            if self.ssid is None or self.ssid == "":
                feedback.config(text="L'SSID non puo' essere vuoto")
                return
            
            if self.password is None or self.password == "":
                feedback.config(text="La password del WiFi non puo' essere vuota")
                return
                
            if self.rpi_username is None or self.rpi_username == "":
                feedback.config(text="Il nuovo username del Raspberry non puo' essere vuoto")
                return
            
            if self.rpi_password is None or self.rpi_password == "":
                feedback.config(text="La nuova password del Raspberry non puo' essere vuota")
                return
               
            regex = re.compile("^[a-z]+://.+$")
            if self.server is None or not regex.match(self.server):
                feedback.config(text="Il server non ha un protocollo valido")
                return
            
            regex = re.compile("^/dev/[a-z0-9]+[a-z]{1}$")
            if self.device is None or not regex.match(self.device):
                feedback.config(text="Il nome del dispositivo non e' corretto")
                return

            self.clean_window()
            self.confirm_window()
            
        avanti = tk.Button(self.window, text="Avanti", command=proceed)
        avanti.grid(row=10, column=1, padx=20, pady=10, sticky=tk.E+tk.S)

        esci = tk.Button(self.window, text="Esci", command=self.window.quit)
        esci.grid(row=10, column=0, padx=20, pady=10, sticky=tk.W+tk.S)


    def confirm_window(self):
        """ Ask for a confirmation of the input given in the input self.window """
        
        confirm = tk.Label(self.window, text="Dati inseriti:\n" + 
            "\nSSID:                 " + self.ssid +
            "\nWIFi Password:        " + self.password +
            "\nServer:               " + self.server +
            "\nServer Username:      " + self.server_username +
            "\nServer Password:      " + self.server_password +
            "\nRaspberry Username:   " + self.rpi_username +
            "\nRaspberry Password:   " + self.rpi_password +
            "\nDispositivo:          " + self.device, justify=tk.LEFT, anchor="w")
        confirm.grid(row=1, columnspan=2, padx=20, pady=10, sticky=tk.W)
        
        confirm1 = tk.Label(self.window, text="Confermi che il dispositivo da formattare e':", justify=tk.LEFT, anchor="w")
        confirm1.grid(row=2, columnspan=2, padx=20, pady=10, sticky=tk.W)
        
        confirm2 = tk.Label(self.window, text=self.device)
        confirm2.grid(row=3, columnspan=2, padx=20, pady=10, sticky=tk.W + tk.E + tk.N + tk.S)
        confirm2.config(font=(None, 20))

        confirm3 = tk.Label(self.window, text="Questa operazione CANCELLERA' tutti i dati dal dispositivo.\nAssicurati che sia il dispositivo giusto prima di proseguire!", justify=tk.LEFT, anchor="w")
        confirm3.grid(row=4, columnspan=2, padx=20, pady=10, sticky=tk.W)
        
        password_label = tk.Label(self.window, text="Inserisci la password per sudo:")
        password_label.grid(row=5, column=0, padx=20, pady=10, sticky=tk.W)
        password = tk.Entry(self.window, show="*")
        password.grid(row=5, column=1, padx=20, pady=10, sticky=tk.E)
        
        def no():
            self.clean_window()
            self.input_window()
        
        no = tk.Button(self.window, text="Indietro", command=no)
        no.grid(row=10, column=0, padx=20, pady=10, sticky=tk.W+tk.S)
        
        def yes():
            self.sudo_pwd = password.get()
            self.clean_window()
            self.install_window()            
            
        yes = tk.Button(self.window, text="Formatta", command=yes)
        yes.grid(row=10, column=1, padx=20, pady=10, sticky=tk.E+tk.S)


    def install_window(self):
        """ Actual installation window """
        self.install = tk.Label(self.window, text="Installazione locale in corso...", justify=tk.LEFT, anchor="w")
        self.install.grid(row=1, columnspan=2, padx=20, pady=10, sticky="ew")
        font = tkfont.Font(font=self.install["font"])
        font["weight"] = "bold"
        self.install.config(font=font)
        
        self.status = scrolledtext.ScrolledText(self.window, wrap = tk.WORD, width="550")
        self.status.grid(row=2, columnspan=2, padx=20, pady=10, sticky="nsew") 
        self.status.bind("<Key>", lambda e: "break")
        
        self.download_os_window()
        
        
    def download_os_window(self):
        """ Downloads the OS """
        self.status.delete('1.0', tk.END)
        self.status.insert(tk.END, "Download del sistema operativo")
        url = "https://downloads.raspberrypi.org/raspios_lite_armhf_latest"
        filename = "raspios_lite_armhf_latest.zip"        
        prefix = " -> Download del sistema operativo"
        t = threading.Thread(target=partial(download, url, filename, self.status, prefix, self.decompress_os))
        t.setDaemon(True)
        t.start()
        
    def decompress_os(self):
        """ Decompress the OS image downloaded before """
        self.status.delete('1.0', tk.END)
        self.status.insert(tk.END, "Decompressione dell'immagine")
        command = ["7z", "e", "-y", "-bsp1", "raspios_lite_armhf_latest.zip"]
        prefix = " -> Decompressione dell'immagine"
        t = threading.Thread(target=partial(execute_command, command, self.status, prefix, self.format_drive))
        t.setDaemon(True)
        t.start()
        
    def format_drive(self):
        """ Renames the image """
        self.status.delete('1.0', tk.END)
        self.status.insert(tk.END, "Formattazione scheda SD")

        # Gets the name of the file
        image_name = subprocess.run(["unzip", "-Z1", "raspios_lite_armhf_latest.zip"], stdout=subprocess.PIPE)
        path_of_image = image_name.stdout.decode('utf-8').strip()
        
        # Format drive
        command = ["dd", "bs=4M", "if="+path_of_image, "of="+self.device, "status=progress", "oflag=direct"]
        prefix = " -> Formattazione scheda SD"
        t = threading.Thread(target=partial(execute_command, command, self.status, prefix, self.copy_files, sudo_pwd=self.sudo_pwd))
        t.setDaemon(True)
        t.start()
        
    def echo_pwd(self):
        return subprocess.Popen(('echo', self.sudo_pwd), stdout=subprocess.PIPE).stdout
        
    def copy_files(self):
        """ Copy essential network configuration (config.txt, ssh and wpa_supplicant.conf) on the PI """
        mount_point = (Path(__file__).parent / ".rpi").absolute()
        self.status.delete('1.0', tk.END)
        self.status.insert(tk.END, " -> Mount di {} sotto {}".format(self.device, mount_point))
        
        # Unmunt everything to make sure the disks can be mounted in a known location (and to sync if needed)
        unmount = subprocess.run(["sudo", "-S", "umount", self.device+"1"], stdin=self.echo_pwd(), stdout=subprocess.PIPE)
        unmount = subprocess.run(["sudo", "-S", "umount", self.device+"2"], stdin=self.echo_pwd(), stdout=subprocess.PIPE)
                
        # Mount boot
        folder = subprocess.run(["mkdir", "-p", mount_point], stdout=subprocess.PIPE)
        mount = subprocess.run(["sudo", "-S", "mount", self.device+"1", mount_point], stdin=self.echo_pwd(), stdout=subprocess.PIPE)
        if not mount or not folder:
            self.status.insert(tk.END, " -> Impossibile aprire la partizione 'boot' sulla SD!\n"+mount.stdout.decode("utf-8"), fg="red")
            quit = tk.Button(self.window, text="Esci", command=self.window.quit)
            quit.grid(row=10, column=0, padx=20, pady=10, sticky=tk.E+tk.S)
            return
        
        # Write the files on boot
        cp_config = subprocess.run(["sudo", "-S", "cp", Path(__file__).parent/"config.txt", mount_point/"config.txt"], stdin=self.echo_pwd(), stdout=subprocess.PIPE)
        touch_ssh = subprocess.run(["sudo", "-S", "touch", mount_point/"ssh"], stdin=self.echo_pwd(), stdout=subprocess.PIPE)
            
        # Unmount boot
        unmount = subprocess.run(["sudo", "-S", "umount", self.device+"1"], stdin=self.echo_pwd(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if not unmount:
            self.status.insert(tk.END, " -> Impossibile smontare la partizione 'boot' sulla SD!\n"+unmount.stdout.decode("utf-8"), fg="red")
            quit = tk.Button(self.window, text="Esci", command=self.window.quit)
            quit.grid(row=10, column=0, padx=20, pady=10, sticky=tk.E+tk.S)
            return

        # Mount rootfs            
        mount = subprocess.run(["sudo", "-S", "mount", self.device+"2", mount_point], stdin=self.echo_pwd(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if not mount:
            self.status.insert(tk.END, " -> Impossibile aprire la partizione 'rootfs' sulla SD!\n"+mount.stdout.decode("utf-8"), fg="red")
            quit = tk.Button(self.window, text="Esci", command=self.window.quit)
            quit.grid(row=10, column=0, padx=20, pady=10, sticky=tk.E+tk.S)
            return

        # Write wpa_supplicant.conf
        with open(Path(__file__).parent/"wpa_supplicant.conf", "w") as f:
            f.writelines("""
            ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
            update_config=1

            network={{
                ssid="{}"
                psk="{}"
            }}
            """.format(self.ssid, self.password))
        wpa_conf = subprocess.run(["sudo", "-S", "cp", Path(__file__).parent/"wpa_supplicant.conf", mount_point/"etc"/"wpa_supplicant"/"wpa_supplicant.conf"], stdin=self.echo_pwd(), stdout=subprocess.PIPE)
        
        # Unmount rootfs 
        ps = subprocess.Popen(('echo', self.sudo_pwd), stdout=subprocess.PIPE)
        unmount = subprocess.run(["sudo", "-S", "umount", self.device+"2"], stdin=self.echo_pwd(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if not unmount:
            self.status.insert(tk.END, " -> Impossibile smontare la partizione 'rootfs' sulla SD!\n"+unmount.stdout.decode("utf-8"), fg="red")
            quit = tk.Button(self.window, text="Esci", command=self.window.quit)
            quit.grid(row=10, column=0, padx=20, pady=10, sticky=tk.E+tk.S)
            return
            
        self.install.config(text="Installazione locale completata.")
        
        self.status.delete('1.0', tk.END)
        self.status.insert(tk.END, "Installazione completata. Smonta la SD, inseriscila nel "
            "Raspberry Pi e attendi qualche secondo. Dopodiche' premi 'Continua'.")
            
        def goto_search_pi():
            proceed.grid_forget()
            self.search_pi()
          
        proceed = tk.Button(self.window, text="Continua", command=goto_search_pi)
        proceed.grid(row=10, column=0, padx=20, pady=10, sticky=tk.E+tk.S)
            
        
    def search_pi(self):
        # Launch nmap scan to find the Raspberry Pi IP
        self.install.config(text="Ricerca Raspberry Pi.")
        self.status.delete('1.0', tk.END)
        message = "La ricerca richiede qualche minuto. Una volta che \
hai identificato l'IP del Raspberry Pi nella lista qua sotto, \
copialo nella casella di testo in basso e premi 'Continua.'\n\n"
        
        previous_index = len(message) + 3
        self.status.insert(tk.END, message)
        
        self.status.insert(tk.END, "Ricerca in corso...\n\n")
        
        ip_box_label = tk.Label(self.window, text="IP:", justify=tk.LEFT, anchor="w")
        ip_box_label.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
        ip_box = tk.Entry(self.window)
        ip_box.grid(row=4, column=1, padx=20, pady=10, sticky=tk.E)
        
        t = threading.Thread(target=partial(self.execute_search_pi, self.status, previous_index))
        t.setDaemon(True)
        t.start()
        
        def repeat_search():
            ip_box_label.grid_forget()
            ip_box.grid_forget()
            repeat.grid_forget()
            proceed.grid_forget()
            self.search_pi()
             
        repeat = tk.Button(self.window, text="Ripeti Ricerca", command=repeat_search)
        repeat.grid(row=10, column=0, padx=20, pady=10, sticky=tk.W+tk.S)

        def goto_ansible():
            self.ip = ip_box.get()
            ip_box.grid_forget()
            ip_box_label.grid_forget()
            repeat.grid_forget()
            proceed.grid_forget()
            self.ansible()   
                            
        proceed = tk.Button(self.window, text="Continua", command=goto_ansible)
        proceed.grid(row=10, column=1, padx=20, pady=10, sticky=tk.E+tk.S)
        
    def execute_search_pi(self, text, starting_index):
        # Actually perform the scan with Nmap""
        command = ["nmap", "-p", "22", "192.168.1,2.0/24"]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        line = ""
        for c in iter(lambda: process.stdout.read(1), b''):
            if c == b'\n' or c == b'\r':
                if "Nmap scan report for" in line:
                    line = line.replace("Nmap scan report for", " - ")
                    text.insert(tk.END, line+"\n")
                line = ""
            else:
                line += c.decode("utf-8")
        
    def ansible(self):
        # Launch the Ansible playbook
        self.install.config(text="Installazione remota in corso...")
        self.status.delete('1.0', tk.END)
        self.status.insert(tk.END, "Preparazione installazione remota (richiede diversi minuti):\n\n")
        
        # Remove host from .ssh/known_hosts if it was present
        remove_ssh_host = subprocess.run(["ssh-keygen", "-R", self.ip], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        t = threading.Thread(target=self.execute_ansible)
        t.setDaemon(True)
        t.start()
        
        
    def execute_ansible(self):
        # Encrypts the rpi password to make it a valid Linux user password
        # Depends on the 'whois' system package
        self.status.insert(tk.END, f"* Change default Raspberry Pi user to {self.rpi_username}\n\n")
        self.status.insert(tk.END, "-> Hashing password\n")
        hashing_proc = subprocess.run(["mkpasswd", "--method=sha-512", self.rpi_password], stdout=subprocess.PIPE)
        hashed_password = hashing_proc.stdout.decode('utf-8').strip()
        # Generate single-use ssh keys
        self.status.insert(tk.END, "-> Creating SSH keys\n")
        key = subprocess.run(["ssh-keygen", "-f", "~/.ssh/zanzocam_id_rsa", "-t", "rsa", "-N", "''"], input=b"y\n", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        
        ansible_path = (Path(__file__).parent/"ansible").absolute()
        with open(ansible_path/"inventory", "w") as i:
            inventory = f"""
            [all]
            {self.ip}
            
            [all:vars]
            ansible_connection=ssh
            ansible_user={self.rpi_username}
            ansible_ssh_pass={self.rpi_password}
            server_url="{self.server}"
            server_username="{self.server_username}"
            server_password="{self.server_password}"
            rpi_user="{self.rpi_username}"
            rpi_plaintext_password="{self.rpi_password}"
            rpi_hashed_password="{hashed_password}"
            """
            i.writelines(inventory)
            
        python_stdout = sys.stdout
        ansible_stdout = RedirectText(self.status)
        try:
            sys.stdout = ansible_stdout  
            try:  
                r = ansible_runner.run(private_data_dir=str(ansible_path), playbook=str(ansible_path/"rpi_custom_user.yml"))
            except:
                # Let's ignore for now, the new user might just be there already
                pass
                        
            self.status.insert(tk.END, f"\n* Installing Zanzocam\n\n")
            r = ansible_runner.run(private_data_dir=str(ansible_path), playbook=str(ansible_path/"rpi_setup.yml"))
            self.end()
            
        except Exception as e:
            def retry_ansible():
                self.status.delete('1.0', tk.END)
                retry.grid_forget()
                quit.grid_forget()
                self.ansible()
            
            retry = tk.Button(self.window, text="Riprova", command=retry_ansible)
            retry.grid(row=10, column=0, padx=20, pady=10, sticky=tk.W+tk.S)
            
            quit = tk.Button(self.window, text="Esci", command=self.window.quit)
            quit.grid(row=10, column=1, padx=20, pady=10, sticky=tk.E+tk.S)
        
        finally:
            sys.stdout = python_stdout
            
            
    def end(self):
        self.install.config(text="Installazione remota completata")
        self.status.delete('1.0', tk.END)
        self.status.insert(tk.END, "Il Raspberry Pi sta mandando foto al server "
        "ogni 5 minuti. Assicurati che anche il server sia configurato "
        "in maniera appropriata.")
        
        end = tk.Button(self.window, text="Fine", command=self.window.quit)
        end.grid(row=10, column=0, padx=20, pady=10, sticky=tk.E+tk.S)
        


class RedirectText:
    def __init__(self, text_ctrl):
        self.output = text_ctrl
    
    def flush(self):
        pass
        
    def write(self, string):
        if ("fatal" in string or "ERROR!" in string) and "ignoring" not in string:
            self.output.insert(tk.END, f"\n\nERRORE!\n\n{string}")
            raise ValueError("Ansible failed:  " + string)

        if "TASK" in string:
            string = string.replace("*", "")
            string = string.replace("TASK [", " ")
            string = string.replace("]", "")
            string = string.strip()                
            if string != "" and not "ok: " in string:
                self.output.insert(tk.END, "-> "+string+"\n")
            
            

def download(url, filename, output_text, prefix, next_function):
    output_text.insert(tk.END, prefix)

    with open(filename, 'ab') as f:
        headers = {}
        pos = f.tell()
        if pos:
            headers['Range'] = f'bytes={pos}-'
        
        response = requests.get(url, headers=headers, stream=True)
        total = response.headers.get('content-length')  
        
        if total is None:
            f.write(response.content)
        else:
            total = int(total)
            downloaded = pos
            for data in response.iter_content(chunk_size=max(int(total/1000), 1024*1024)):
                downloaded += len(data)
                f.write(data)
                done = int(100*downloaded/total)
                bar = "|" * done 
                empty_space = '.' * (100-done-1)
                total_size = math.ceil(total/1000000)
                output_text.delete('1.0', tk.END)
                output_text.insert(tk.END, "{} ({} MB): {}%\n\n|{}{}|\n".format(prefix, total_size, done, bar, empty_space))
    
    next_function()


def execute_command(commands, output_text, prefix, next_function, sudo_pwd=None):
    if sudo_pwd:
        ps = subprocess.Popen(('echo', sudo_pwd), stdout=subprocess.PIPE)
        process = subprocess.Popen(["sudo", "-S"] + commands, stdin=ps.stdout, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    else:
        process = subprocess.Popen(commands, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    string = ""
    for c in iter(lambda: process.stdout.read(1), b''):
        if c == b'\n' or c == b'\r':
            string = ""
        elif c == b'\x08':
            string = string[:-1]
        else:
            string += c.decode("utf-8")
        output_text.delete('1.0', tk.END)
        output_text.insert(tk.END, "{}\n\n{}\n".format(prefix, string))                
    next_function()    
        

if "__main__" == __name__:
    Wizard()
