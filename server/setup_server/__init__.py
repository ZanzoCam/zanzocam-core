import os
import json
from flask import Flask, render_template, request

app = Flask(__name__)


initial_data = "/var/www/setup-server/setup_server/initial_data.json"


@app.route("/", methods=["GET"])
def setup():
    try:
        with open(initial_data, 'r') as d:
            data = json.load(d)
    except Exception:
        data = {}
    return render_template("setup.html", title="Setup", data=data)


    
@app.route("/setting-up", methods=["POST"])
def setting_up():
    return render_template("setting-up.html", title="Setting up...")
        
    
@app.route("/setup", methods=["POST"])
def setup():
        
        # Save new initial data to a file
        with open(initial_data, 'w') as d:
            json.dump(request.form, d)

        # Setup the Pi accordingly
        
        # Encrypts the rpi password to make it a valid Linux user password
        # Depends on the 'whois' system package
        hashing_proc = subprocess.run(["mkpasswd", "--method=sha-512", request.form.rpi_password], stdout=subprocess.PIPE)
        hashed_password = hashing_proc.stdout.decode('utf-8').strip()
        
        ansible_path = (Path(__file__).parent/"ansible").absolute()
        with open(ansible_path / "inventory", "w") as i:
            inventory = f"""
            [all]
            {self.ip}
            
            [all:vars]
            wifi_ssid="{request.form.wifi_ssid}"
            wifi_password="{request.form.wifi_password}"

            server_url="{request.form.server_url}"
            server_username="{request.form.server_username}"
            server_password="{request.form.server_password}"

            rpi_user="{request.form.rpi_username}"
            rpi_plaintext_password="{request.form.rpi_password}"
            rpi_hashed_password="{hashed_password}"
            
            crontab_minute="{request.form.crontab_minute}"
            crontab_hour="{request.form.crontab_hour}"
            crontab_day="{request.form.crontab_day}"
            crontab_month="{request.form.crontab_month}"
            crontab_weekday="{request.form.crontab_weekday}"

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
        
        


    # Load any previously stored initial data
    try:
        with open(initial_data, 'r') as d:
            data = json.load(d)
    except Exception:
        data = {}
    return render_template("setup.html", title="Setup", data=data)

