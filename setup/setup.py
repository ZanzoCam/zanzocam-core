# sudo apt-get install python3-pip python3-tk
# pip3 install tk requests

import os
import re
import sys
import math
import requests
import threading
import subprocess
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from functools import partial
from threading import Event, Thread
from urllib.request import urlretrieve


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
        
        title = tk.Label(self.window, text="Setup ZANZOCAM")
        title.grid(row=0, columnspan=2, padx=20, pady=20, sticky=tk.W + tk.E + tk.N + tk.S)
        title.config(font=(None, 22))

        if self.deps_are_installed():
            self.install_window()
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
        avanti.grid(row=6, column=1, padx=20, pady=10, sticky=tk.E)

        esci = tk.Button(self.window, text="Esci", command=self.window.quit)
        esci.grid(row=6, column=0, padx=20, pady=10, sticky=tk.W)


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
        confirm3.grid(row=4, padx=20, pady=10, sticky=tk.W)
        
        def no():
            self.clean_window()
            self.input_window()
        
        no = tk.Button(self.window, text="No", command=no)
        no.grid(row=5, column=0, padx=20, pady=10, sticky=tk.W)
        
        def yes():
            self.clean_window()
            self.install_window()            
            
        yes = tk.Button(self.window, text="Si", command=yes)
        yes.grid(row=5, column=1, padx=20, pady=10, sticky=tk.E)


    def install_window(self):
        """ Actual installation window """
        install = tk.Label(self.window, text="Installazione in corso:")
        install.grid(row=1, padx=20, pady=0)
        
        self.status = tk.Label(self.window, text="", justify=tk.LEFT, anchor="w")
        self.status.grid(row=1, padx=20, pady=0) 
        #self.download_os_window()
        self.decompress_os()

    def download_os_window(self):
        """ Downloads the OS """
        url = "https://downloads.raspberrypi.org/raspios_lite_armhf_latest"
        filename = "raspios_lite_armhf_latest.zip"        
        prefix = "Download del sistema operativo: "
        t = threading.Thread(target=partial(download, url, filename, self.status, prefix, self.decompress_os))
        t.setDaemon(True)
        t.start()
        
    def decompress_os(self):
        """ Decompress the OS image downloaded before """
        command = ["7z", "e", "-y", "-bsp1", "raspios_lite_armhf_latest.zip"]
        prefix = "Decompressione dell'immagine:"
        t = threading.Thread(target=partial(execute_command, command, self.status, prefix, self.format_drive))
        t.setDaemon(True)
        t.start()
        
    def format_drive(self):
        # Rename file
        self.status.config(text="Normalizzazione del nome del sistema operativo")
        image_name = subprocess.run(["unzip", "-Z1", "raspios_lite_armhf_latest.zip"], stdout=subprocess.PIPE)
        path_of_image = image_name.stdout.decode('utf-8').strip()
        os.rename(path_of_image, "rpios.img")

        # Format drive
        command = ["7z", "e", "raspios_lite_armhf_latest.zip"]
        prefix = "Formattazione scheda SD:"
        t = threading.Thread(target=partial(execute_command, command, self.status, prefix, format_drive))
        t.setDaemon(True)
        t.start()
        
        
        #command = "sudo dd bs=4M if=raspios.img of={} status=progress oflag=direct".format(device)
        #t = threading.Thread(target=partial(format_drive, command))
        #t.setDaemon(True)
        #t.start()
           
        
        
        
        
def download(url, filename, output_label, prefix, next_function):
    output_label.config(text=prefix)

    with open(filename, 'wb') as f:
        response = requests.get(url, stream=True)
        total = response.headers.get('content-length')

        if total is None:
            f.write(response.content)
        else:
            downloaded = 0
            total = int(total)
            for data in response.iter_content(chunk_size=max(int(total/1000), 1024*1024)):
                downloaded += len(data)
                f.write(data)
                done = int(100*downloaded/total)
                bar = "|" * done 
                empty_space = '.' * (100-done-1)
                total_size = math.ceil(total/1000000)
                output_label.config(text="{} ({} MB): {}%\n\n|{}{}|\n".format(prefix, total_size, done, bar, empty_space))
    
    next_function()


def execute_command(commands, output_label, prefix, next_function):
    process = subprocess.Popen(commands, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    string = r""
    for c in iter(lambda: process.stdout.read(1), b''):
        string += c.decode("utf-8")
        print(c)
        if c == b'\n':
            output_label.config(text=r"{}\n\n{}\n".format(prefix, string))
            string = r""
    next_function()    
        

if "__main__" == __name__:
    Wizard()
