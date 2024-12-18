import ivtools
import click
from time import sleep
from tabulate import tabulate  # To create formatted tables

# List of bias vectors to iterate over
BIAS_VECTORS = [[0, 0, 0, 0, 0]]  # Example vectors

@click.command()
@click.option("--ip_address", '-ip', default='6', help="IP Address (default: 6)")
def main(ip_address):
    # Validate IP address
    if ip_address != "6":
        print("\033[91mInvalid IP address! Only endpoint 6 is supported.\033[0m")
        return

    ip = "10.73.137.107"
    print(f"Configuring endpoint {ip} for multiple bias vectors...")
    interface = ivtools.Daphne(ip)

    # Table header
    table_data = [["Vector Index", "AFE", "Applied Voltage (DAC)", "Read Bias (V)"]]

    # Iterate over each bias vector
    for idx, voltages in enumerate(BIAS_VECTORS, start=1):
        print(f"\nApplying Bias Vector {idx}: {voltages}")
        try:
            # Disable bias
            interface.command('WR VBIASCTRL V 0')

            # Apply the voltages
            for AFE, voltage in enumerate(voltages):
                interface.command(f'WR BIASSET AFE {AFE} V {voltage}')

            # Enable bias
            interface.command('WR VBIASCTRL V 4095')
            sleep(1)

            # Read and collect bias values for each AFE
            bias_data = interface.read_bias()  # Assuming read_bias returns a dictionary of bias values
            for AFE, voltage in enumerate(voltages):
                read_bias = bias_data.get(f"VBIAS{AFE}", "N/A")
                table_data.append([idx, AFE, voltage, read_bias])

        except Exception as e:
            print(f"\033[91mError applying Bias Vector {idx}: {e}\033[0m")
            continue  # Proceed to the next vector if there's an error

    # Print the table of results
    print("\n\033[92mBias Vector Configuration Results:\033[0m")
    print(tabulate(table_data, headers="firstrow", tablefmt="grid"))

if __name__ == "__main__":
    main()