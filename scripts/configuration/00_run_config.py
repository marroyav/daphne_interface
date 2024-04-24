
import subprocess

# List of scripts to run
config_scripts = ["conf_clocks.py", 
                  "conf_analog.py", 
                  "conf_datamodes.py",
                  "conf_trigger.py",
                  ]

# Execute the scripts
for script in config_scripts: subprocess.run(["python", script])