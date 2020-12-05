from pathlib import Path

try:
    sys.stdout = ansible_stdout    
    
    from ansible_runner.interface import init_runner
    r = init_runner(private_data_dir=str(ansible_path), playbook=str(ansible_path/"initial_setup.yml"))
    
    #self.status.config(text=str(r.config.command)+"  "+str(r.config.cwd)+"  "+str(r.config.env))
    #return
    
    r.run()
    #r = ansible_runner.run(private_data_dir=ansible_path, playbook=ansible_path/"initial_setup.yml")

    # Process ansible output
    string = ""
    for c in iter(lambda: ansible_stdout.read(1), ''):
        if c == '\n' or c == '\r':
            if "fatal" in string:
                self.status.config(text=f"ERRORE!\n\n{string}")
                
                def retry_ansible():
                    retry.grid_forget()
                    quit.grid_forget()
                    self.ansible()
                
                retry = tk.Button(self.window, text="Riprova", command=retry_ansible)
                retry.grid(row=8, column=0, padx=20, pady=10, sticky=tk.W+tk.S)
                
                quit = tk.Button(self.window, text="Esci", command=self.window.quit)
                quit.grid(row=8, column=1, padx=20, pady=10, sticky=tk.E+tk.S)
                

            #if "TASK" in string:
            string = string.replace("*", "")
            string = string.replace("TASK [", " ")
            string = string.replace("PLAY [", " ")
            string = string.replace("]", "")                     
            if string != "" and not "ok: " in string:
                self.status.config(text="{}\n-> {}".format(self.status.cget("text"), string))
            string = ""
        else:
            string += c
            
    
    print("FINEEE")

finally:
    sys.stdout = python_stdout
    output_string = ansible_stdout.getvalue()
    ansible_stdout.close() 
