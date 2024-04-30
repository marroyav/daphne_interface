import subprocess, click

@click.command()
@click.option("--ip_address", '-ip', default='ALL',help="IP Address")
def run_checks(ip_address):
    '''
    With this script we configure the DAQ for taking data.
    The following scripts are executed:
        - checks_datamodes.py: checks the datamode for each endpoint previously configured with conf_datamodes.py
        - checks_endpoints.py: verify the clocks and timing endpoint is in a good state
        - checks_timestamp.py: checks that the configured timestamp is OK
    Arguments:
        - ip_address (deafult='ALL'): values of the endpoints you want to configure the DAQ.
    Example:
        python 01_run_checks.py --ip_address 4,5
    '''

    print("\033[94m[INFO] Welcome to the script for checking that the DAQ config is OK!")
    print("\033[94m By executing the script as: python 01_run_checks.py all the endpoints (IPs) will be configured.")
    print("\033[94m For running over personalized IP(s) run: python 01_run_checks.py --ip_address 4,5 ")
    print(" Enjoy! :) \n \033[0m")

    confirmation = input(f"Are you sure you want to continue with IP(s): [{ip_address}]? (y/n): ")
    if confirmation.lower() not in ['true', '1', 't', 'y', 'yes']: exit()

    # Safety check to make sure that the IP address is valid
    for ip in list(map(int, list(ip_address.split(",")))):
        if ip not in [4,5,7,9,11,12,13]: 
            print("\033[91mInvalid IP address, please choose your ip between 4,5,7,9,11,12,13 :)\033[0m"); 
            exit()

    # List of scripts to run
    config_scripts = ["check_datamodes.py", 
                      "check_endpoints.py", 
                      "check_timestamp.py"]

    # Execute the scripts
    for script in config_scripts: 
        print(f'\033[92m\nExecuting {script}\033[0m')
        command = ["python", script, "--ip_address", ip_address]
        subprocess.run(command)

if __name__ == '__main__':
    run_checks()