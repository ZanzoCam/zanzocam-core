# sudo apt-get install python3-pip python3-tk
# pip3 install tk

import os
import re
import tkinter as tk

class Wizard:

    def __init__(self):
        self.ssid = None
        self.password = None
        self.server = None
        self.device = None
    
        window = tk.Tk()
        window.title("Setup ZANZOCAM")
        window.option_add('*Font', '18')
        
        title = tk.Label(window, text="Setup ZANZOCAM")
        title.grid(row=0, columnspan=2, padx=20, pady=20, sticky=tk.W + tk.E + tk.N + tk.S)
        title.config(font=(None, 22))

        self.input_window(window)
                
        window.mainloop()

    def input_window(self, window):
        ssid_label = tk.Label(window, text="WiFi SSID")
        ssid_label.grid(row=1, column=0, padx=20, pady=10, sticky=tk.W)
        ssid = tk.Entry(window)
        ssid.grid(row=1, column=1, padx=20, pady=10, sticky=tk.E)

        password_label = tk.Label(window, text="WiFi Password")
        password_label.grid(row=2, column=0, padx=20, pady=10, sticky=tk.W)
        password = tk.Entry(window)
        password.grid(row=2, column=1, padx=20, pady=10, sticky=tk.E)

        server_label = tk.Label(window, text="Server URL")
        server_label.grid(row=3, column=0, padx=20, pady=10, sticky=tk.W)
        server = tk.Entry(window)
        server.grid(row=3, column=1, padx=20, pady=10, sticky=tk.E)

        device_label = tk.Label(window, text="Posizione SD (/dev/sdX)")
        device_label.grid(row=4, column=0, padx=20, pady=10, sticky=tk.W)
        device = tk.Entry(window)
        device.grid(row=4, column=1, padx=20, pady=10, sticky=tk.E)
        
        feedback = 0

        def proceed():
            self.ssid = ssid.get()
            self.password = password.get()
            self.server = server.get()
            self.device = device.get()
            
            feedback = tk.Label(window, text="", fg="red")

            if self.ssid is None or self.ssid == "":
                feedback.config(text="SSID non puo' essere vuoto")
                feedback.grid(row=5, columnspan=2, padx=10, pady=10, sticky=tk.W + tk.E) 
                return
            
            if self.password is None or self.password == "":
                feedback.config(text="la password non puo' essere vuota")
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
            
            ssid_label.grid_forget()
            ssid.grid_forget()
            password_label.grid_forget()
            password.grid_forget()
            server_label.grid_forget()
            server.grid_forget()
            device_label.grid_forget()
            device.grid_forget()
            avanti.grid_forget()
            esci.grid_forget()
            feedback.grid_forget()
            feedback.config(text="")
            self.progress_window(window)
            
        avanti = tk.Button(window, text="Avanti", command=proceed)
        avanti.grid(row=6, column=1, padx=20, pady=10, sticky=tk.E)

        esci = tk.Button(window, text="Esci", command=window.quit)
        esci.grid(row=6, column=0, padx=20, pady=10, sticky=tk.W)


    def progress_window(self, window):
        confirm = tk.Label(window, text="Dati inseriti:\n" + 
            "\nSSID:        " + self.ssid +
            "\nPassword:    " + self.password +
            "\nServer:      " + self.server +
            "\nDispositivo: " + self.device, justify=tk.LEFT, anchor="w")
        confirm.grid(row=1, padx=20, pady=10, sticky=tk.W)
        
        confirm1 = tk.Label(window, text="Confermi che il dispositivo da formattare e':", justify=tk.LEFT, anchor="w")
        confirm1.grid(row=2, padx=20, pady=10, sticky=tk.W)
        
        confirm2 = tk.Label(window, text=self.device)
        confirm2.grid(row=3, columnspan=2, padx=20, pady=10, sticky=tk.W + tk.E + tk.N + tk.S)

        confirm3 = tk.Label(window, text="Questa operazione CANCELLERA' tutti i dati dal dispositivo.\nAssicurati che sia il dispositivo giusto prima di proseguire!", justify=tk.LEFT, anchor="w")
        confirm3.grid(row=4, padx=20, pady=10, sticky=tk.W)
        
        def no():
            confirm.grid_forget()
            confirm1.grid_forget()
            confirm2.grid_forget()
            confirm3.grid_forget()
            yes.grid_forget()
            no.grid_forget()
            self.input_window(window)
        
        no = tk.Button(window, text="No", command=no)
        no.grid(row=5, column=0, padx=20, pady=10, sticky=tk.W)
        
        def yes():
            confirm.grid_forget()
            confirm1.grid_forget()
            confirm2.grid_forget()
            confirm3.grid_forget()
            yes.grid_forget()
            no.grid_forget()
            
            
        yes = tk.Button(window, text="Si", command=yes)
        yes.grid(row=5, column=1, padx=20, pady=10, sticky=tk.E)


if "__main__" == __name__:
    Wizard()
