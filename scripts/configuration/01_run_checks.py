import subprocess

# List of scripts to run
config_scripts = ["check_datamodes.py", 
                  "check_endpoints.py", 
                  "check_timestamp.py"]

# Execute the scripts
for script in config_scripts: subprocess.run(["python", script])