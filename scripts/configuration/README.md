# DAPHNE CONFIGURATION FOR PDS DATA TAKING

In this folder we can find the scripts used for the configuration of DAPHNE prior data taking.
The scripts can be run individually but you can also find two general scripts that run all the workflow.

## Configuration
Run the following command:
```bash
python 00_run_config.py
```
This deafult configuration will run over all endpoints (IPs). If you want to run only over a personalized set of IPs you can use the ```--ip_address (-ip)``` flag, i.e. ``` python 00_run_config.py -ip 4(,5)```.
**Separating by commas all the endpoints**. A security confimation is added to avoid running by error over all IPs.

With this script the following scripts are executed to initialize DAPHNE analog chain:
    - conf_clocks.py: configures the timing interface
    - conf_analog.py: configures the analog chain
    - conf_datamodes.py: configures the data modes for each endpoint
    - conf_trigger.py: configuration only for the full-streaming endpoints [4,5,7] (if other introduced a warning is printed and continues)

## Checks

In a similar way, once we have configured the DAQ we need to check that everything is OK to run.
By running:
```bash
python 01_run_checks.py
```
The following scripts are executed to confirm we can take data:
    - checks_datamodes.py: checks the datamode for each endpoint previously configured with conf_datamodes.py
    - checks_endpoints.py: verify the clocks and timing endpoint is in a good state
    - checks_timestamp.py: checks that the configured timestamp is OK