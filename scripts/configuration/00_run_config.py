
import subprocess, click

@click.command()
@click.option("--ip_address", '-ip', default='ALL',help="IP Address")
def run_config(ip_address):
    '''
    With this script we configure the DAQ for taking data.
    The following scripts are executed to initialize DAPHNE analog chain:
        - conf_clocks.py: configures the timing interface
        - conf_analog.py: configures the analog chain
        - conf_datamodes.py: configures the data modes for each endpoint
        - conf_trigger.py: configuration only for the full-streaming endpoints [4,5,7] (if other introduced a warning is printed and continues)
    Arguments:
        - ip_address (deafult='ALL'): values of the endpoints you want to configure the DAQ.
    Example:
        python 00_run_config.py --ip_address 4,5
    '''

    print("\033[94m[INFO] Welcome to the script for configuring the DAQ!")
    print("\033[94m By executing the script as: python 00_run_config.py all the endpoints (IPs) will be configured.")
    print("\033[94m For running over personalized IP(s) run: python 00_run_config.py --ip_address 4,5 ")
    print(" Enjoy! :) \n \033[0m")

    confirmation = input(f"Are you sure you want to continue with IP(s): [{ip_address}]? (y/n): ")
    if confirmation.lower() not in ['true', '1', 't', 'y', 'yes']: exit()

    # Safety check to make sure that the IP address is valid
    if ip_address=="ALL": pass
    else:
        for ip in list(map(int, list(ip_address.split(",")))):
            if ip not in [4,5,7,9,11,12,13]: 
                print("\033[91mInvalid IP address, please choose your ip between 4,5,7,9,11,12,13 :)\033[0m"); 
                exit()

    # List of scripts to run
    config_scripts = ["conf_clocks.py", 
                      "conf_analog.py", 
                      "conf_datamodes.py",
                      "conf_trigger.py"]

    # Execute the scripts
    for script in config_scripts:
        print(f'\033[92m\nExecuting {script}\033[0m')
        command = ["python", script, "--ip_address", ip_address]
        subprocess.run(command)

if __name__ == '__main__':
    run_config()