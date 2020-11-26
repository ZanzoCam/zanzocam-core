# sudo apt-get install python3-pip python3-tk
# pip3 install tk requests

import os
import re
import sys
import math
import time
import shutil
import requests
import threading
import subprocess
from pathlib import Path
from functools import partial
from threading import Event, Thread

import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont 


class Wizard:

    def __init__(self):
        """ Create the root self.window and the title, then go to the first self.window """
        
        self.ssid = None
        self.password = None
        self.server = None
        self.device = None
    
        self.window = tk.Tk()
        self.window.title("Setup ZANZOCAM")
        self.window.option_add('*Font', '18')
        
        self.window.columnconfigure(0, weight=1)
        self.window.columnconfigure(1, weight=1)
        self.window.rowconfigure(6, weight=1)
        self.window.geometry("600x500")
        
        title = tk.Label(self.window, text="Setup ZANZOCAM")
        title.grid(row=0, columnspan=2, padx=20, pady=20, sticky=tk.W + tk.E + tk.N + tk.S)
        title.config(font=(None, 22))

        if self.deps_are_installed():
            self.input_window()
        self.window.mainloop()
        
    def clean_window(self):
        """ Removes all the items from the window apart from the title """
        for item in self.window.grid_slaves():
            if int(item.grid_info()["row"]) > 0:
                item.grid_forget()

    def deps_are_installed(self):
        """ Verifies that all the dependencies are present on the system """
        result = subprocess.Popen("./check_deps.sh")
        text = result.communicate()[0]
        returncode = result.returncode
        
        feedback = tk.Label(self.window, text="", fg="red")
        feedback.grid(row=5, columnspan=2, padx=10, pady=10, sticky=tk.W + tk.E + tk.N + tk.S)
            
        if returncode != 0:
            feedback.config(text="Dipendenze mancanti! Esegui:\n\n"+
            "sudo apt-get install 7z lsblk dd git sshfs" +
            "\n\ndopodiche' chiudi e riapri questo installer.")
            
            esci = tk.Button(self.window, text="Esci", command=self.window.quit)
            esci.grid(row=6, columnspan=2, padx=20, pady=10, sticky=tk.W +tk.E)
            return False
        return True
        
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

        device_label = tk.Label(self.window, text="Posizione SD (/dev/sdX)")
        device_label.grid(row=4, column=0, padx=20, pady=10, sticky=tk.W)
        device = tk.Entry(self.window)
        device.grid(row=4, column=1, padx=20, pady=10, sticky=tk.E)
        
        feedback = tk.Label(self.window, text="", fg="red")
        feedback.grid(row=5, columnspan=2, padx=10, pady=10, sticky=tk.W + tk.E + tk.N + tk.S)
        
        def proceed():
            """ Validates the input and cleans up the root self.window """
            
            self.ssid = ssid.get()
            self.password = password.get()
            self.server = server.get()
            self.device = device.get()
            
            if self.ssid is None or self.ssid == "":
                feedback.config(text="L'SSID non puo' essere vuoto")
                feedback.grid(row=5, columnspan=2, padx=10, pady=10, sticky=tk.W + tk.E) 
                return
            
            if self.password is None or self.password == "":
                feedback.config(text="La password non puo' essere vuota")
                feedback.grid(row=5, columnspan=2, padx=10, pady=10, sticky=tk.W + tk.E) 
                return
               
            regex = re.compile("^[a-z]+://.+$")
            if self.server is None or not regex.match(self.server):
                feedback.config(text="Il server non ha un protocollo valido")
                feedback.grid(row=5, columnspan=2, padx=10, pady=10, sticky=tk.W + tk.E) 
                return
            
            regex = re.compile("^/dev/[a-z0-9]+[a-z]{1}$")
            if self.device is None or not regex.match(self.device):
                feedback.config(text="Il nome del dispositivo non e' corretto")
                feedback.grid(row=5, columnspan=2, padx=10, pady=10, sticky=tk.W + tk.E) 
                return
            
            self.clean_window()
            self.progress_window()
            
        avanti = tk.Button(self.window, text="Avanti", command=proceed)
        avanti.grid(row=6, column=1, padx=20, pady=10, sticky=tk.E+tk.S)

        esci = tk.Button(self.window, text="Esci", command=self.window.quit)
        esci.grid(row=6, column=0, padx=20, pady=10, sticky=tk.W+tk.S)


    def progress_window(self):
        """ Ask for a confirmation of the input given in the input self.window """
        
        confirm = tk.Label(self.window, text="Dati inseriti:\n" + 
            "\nSSID:        " + self.ssid +
            "\nPassword:    " + self.password +
            "\nServer:      " + self.server +
            "\nDispositivo: " + self.device, justify=tk.LEFT, anchor="w")
        confirm.grid(row=1, padx=20, pady=10, sticky=tk.W)
        
        confirm1 = tk.Label(self.window, text="Confermi che il dispositivo da formattare e':", justify=tk.LEFT, anchor="w")
        confirm1.grid(row=2, padx=20, pady=10, sticky=tk.W)
        
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
        no.grid(row=6, column=0, padx=20, pady=10, sticky=tk.W+tk.S)
        
        def yes():
            self.sudo_pwd = password.get()
            self.clean_window()
            self.install_window()            
            
        yes = tk.Button(self.window, text="Formatta", command=yes)
        yes.grid(row=6, column=1, padx=20, pady=10, sticky=tk.E+tk.S)


    def install_window(self):
        """ Actual installation window """
        install = tk.Label(self.window, text="Installazione in corso:", justify=tk.LEFT, anchor="w")
        install.grid(row=1, columnspan=2, padx=20, pady=10, sticky="ew")
        font = tkfont.Font(font=install["font"])
        font["weight"] = "bold"
        install.config(font=font)
        
        self.status = tk.Message(self.window, text="", justify=tk.LEFT, anchor="w", width="550")
        self.status.grid(row=2, columnspan=2, padx=20, pady=10, sticky="nsew") 
        self.download_os_window()
        
    def download_os_window(self):
        """ Downloads the OS """
        self.status.config(text="Download del sistema operativo")
        url = "https://downloads.raspberrypi.org/raspios_lite_armhf_latest"
        filename = "raspios_lite_armhf_latest.zip"        
        prefix = " -> Download del sistema operativo"
        t = threading.Thread(target=partial(download, url, filename, self.status, prefix, self.decompress_os))
        t.setDaemon(True)
        t.start()
        
    def decompress_os(self):
        """ Decompress the OS image downloaded before """
        self.status.config(text="Decompressione dell'immagine")
        command = ["7z", "e", "-y", "-bsp1", "raspios_lite_armhf_latest.zip"]
        prefix = " -> Decompressione dell'immagine"
        t = threading.Thread(target=partial(execute_command, command, self.status, prefix, self.format_drive))
        t.setDaemon(True)
        t.start()
        
    def format_drive(self):
        """ Renames the image """
        self.status.config(text="Formattazione scheda SD")

        # Gets the name of the file
        image_name = subprocess.run(["unzip", "-Z1", "raspios_lite_armhf_latest.zip"], stdout=subprocess.PIPE)
        path_of_image = image_name.stdout.decode('utf-8').strip()
        
        # Format drive
        command = ["dd", "bs=4M", "if="+path_of_image, "of="+self.device, "status=progress", "oflag=direct"]
        prefix = " -> Formattazione scheda SD"
        t = threading.Thread(target=partial(execute_command, command, self.status, prefix, self.copy_files, sudo_pwd=self.sudo_pwd))
        t.setDaemon(True)
        #t.start()
        self.copy_files()
        
    def echo_pwd(self):
        return subprocess.Popen(('echo', self.sudo_pwd), stdout=subprocess.PIPE).stdout
        
    def copy_files(self):
        """ Copy essential network configuration (config.txt, ssh and wpa_supplicant.conf) on the PI """
        mount_point = (Path(__file__).parent / ".rpi").absolute()
        self.status.config(text=" -> Mount di {} sotto {}".format(self.device, mount_point))
        
        # Unmunt everything to make sure the disks can be mounted in a known location (and to sync if needed)
        unmount = subprocess.run(["sudo", "-S", "umount", self.device+"1"], stdin=self.echo_pwd(), stdout=subprocess.PIPE)
        unmount = subprocess.run(["sudo", "-S", "umount", self.device+"2"], stdin=self.echo_pwd(), stdout=subprocess.PIPE)
        
        time.sleep(1)
        
        # Mount boot
        folder = subprocess.run(["mkdir", "-p", mount_point], stdout=subprocess.PIPE)
        mount = subprocess.run(["sudo", "-S", "mount", self.device+"1", mount_point], stdin=self.echo_pwd(), stdout=subprocess.PIPE)
        if not mount or not folder:
            print(mount, folder)
            self.status.config(text=" -> Impossibile aprire la partizione 'boot' sulla SD!\n"+mount.stdout.decode("utf-8"), fg="red")
            quit = tk.Button(self.window, text="Esci", command=self.window.quit)
            quit.grid(row=6, column=0, padx=20, pady=10, sticky=tk.E+tk.S)
            return
        
        # Write the files on boot
        cp_config = subprocess.run(["sudo", "-S", "cp", Path(__file__).parent/"files"/"config.txt", mount_point/"config.txt"], stdin=self.echo_pwd(), stdout=subprocess.PIPE)
        touch_ssh = subprocess.run(["sudo", "-S", "touch", mount_point/"ssh"], stdin=self.echo_pwd(), stdout=subprocess.PIPE)
            
        # Unmount boot
        unmount = subprocess.run(["sudo", "-S", "umount", self.device+"1"], stdin=self.echo_pwd(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if not unmount:
            print(unmount)
            self.status.config(text=" -> Impossibile smontare la partizione 'boot' sulla SD!\n"+unmount.stdout.decode("utf-8"), fg="red")
            quit = tk.Button(self.window, text="Esci", command=self.window.quit)
            quit.grid(row=6, column=0, padx=20, pady=10, sticky=tk.E+tk.S)
            return

        # Mount rootfs            
        mount = subprocess.run(["sudo", "-S", "mount", self.device+"2", mount_point], stdin=self.echo_pwd(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if not mount:
            print(mount)
            self.status.config(text=" -> Impossibile aprire la partizione 'rootfs' sulla SD!\n"+mount.stdout.decode("utf-8"), fg="red")
            quit = tk.Button(self.window, text="Esci", command=self.window.quit)
            quit.grid(row=6, column=0, padx=20, pady=10, sticky=tk.E+tk.S)
            return

        # Write wpa_supplicant.conf
        with open(Path(__file__).parent/"files"/"wpa_supplicant.conf", "w") as f:
            f.writelines("""
            ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
            update_config=1

            network={{
                ssid="{}"
                psk="{}"
            }}
            """.format(self.ssid, self.password))
        wpa_conf = subprocess.run(["sudo", "-S", "cp", Path(__file__).parent/"files"/"wpa_supplicant.conf", mount_point/"etc"/"wpa_supplicant"/"wpa_supplicant.conf"], stdin=self.echo_pwd(), stdout=subprocess.PIPE)
        
        # Unmount rootfs 
        ps = subprocess.Popen(('echo', self.sudo_pwd), stdout=subprocess.PIPE)
        unmount = subprocess.run(["sudo", "-S", "umount", self.device+"2"], stdin=self.echo_pwd(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if not unmount:
            print(unmount)
            self.status.config(text=" -> Impossibile smontare la partizione 'rootfs' sulla SD!\n"+unmount.stdout.decode("utf-8"), fg="red")
            quit = tk.Button(self.window, text="Esci", command=self.window.quit)
            quit.grid(row=6, column=0, padx=20, pady=10, sticky=tk.E+tk.S)
            return
            
        self.status.config(text="Installazione completata. Smonta la SD, inseriscila nel "
            "Raspberry Pi e attendi qualche secondo. Dopodiche' premi 'Continua'.")
          
        def goto_search_pi():
            self.clean_window()
            self.search_pi()
            
        quit = tk.Button(self.window, text="Esci", command=goto_search_pi)
        quit.grid(row=6, column=0, padx=20, pady=10, sticky=tk.E+tk.S)
            
        
    def search_pi(self):
        search = tk.Label(self.window, text="Ricerca del Raspberry Pi", justify=tk.LEFT, anchor="w")
        search.grid(row=1, columnspan=2, padx=20, pady=10, sticky="ew")
        
        
        
        
        
        
        
def download(url, filename, output_label, prefix, next_function):
    output_label.config(text=prefix)

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
                output_label.config(text="{} ({} MB): {}%\n\n|{}{}|\n".format(prefix, total_size, done, bar, empty_space))
    
    next_function()


def execute_command(commands, output_label, prefix, next_function, sudo_pwd=None):
    if sudo_pwd:
        ps = subprocess.Popen(('echo', sudo_pwd), stdout=subprocess.PIPE)
        process = subprocess.Popen(["sudo", "-S"] + commands, stdin=self.echo_pwd(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
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
            #print(c)
        output_label.config(text="{}\n\n{}\n".format(prefix, string))                

        
    next_function()    
        

if "__main__" == __name__:
    Wizard()
