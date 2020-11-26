import subprocess
import sys

process = subprocess.Popen(["ping", "www.google.com"], stdout=subprocess.PIPE)
string = ""
for c in iter(lambda: process.stdout.read(1), b''):  # replace '' with b'' for Python 3
    string += c.decode("utf-8")
    if c == b'\n':
        print(string)
        string = ""
