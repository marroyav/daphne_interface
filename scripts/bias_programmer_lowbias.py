import click
from ivtools import Daphne

@click.command()
@click.option("--ip_address", '-ip', default='ALL', help="Last digits of the IP address (comma-separated) or 'ALL'")
def main(ip_address):
    """
    This script writes bias settings to specified IPs or all predefined IPs.
    
    Args:
        - ip_address (default='ALL'): If 'ALL', runs on all predefined IPs.
                                     If digits, runs only on those endpoints.

    Example:
        python write_bias.py --ip_address 4,5
        python write_bias.py --ip_address ALL
    """
    # Define IP-to-Bias Mapping
    bias_map = {
        4: [821, 1280, 0, 0, 0],
        5: [852, 846, 1303, 0, 0],
        7: [0, 0, 0, 0, 0],
        9: [842, 879, 1274, 1300, 1265],
        10: [850, 1393, 0, 0, 0],
        11: [847, 853, 822, 1211, 1297],
        12: [1288, 1296, 1280, 1313, 1300],
        13: [848, 0, 0, 0, 0],
    }

    # Process input argument
    if ip_address.upper() == "ALL":
        selected_ips = list(bias_map.keys())
    else:
        try:
            selected_ips = list(map(int, ip_address.split(",")))
        except ValueError:
            print("\033[91mInvalid IP address input. Use 'ALL' or comma-separated numbers.\033[0m")
            return

    # Validate selected IPs
    invalid_ips = [ip for ip in selected_ips if ip not in bias_map]
    if invalid_ips:
        print(f"\033[91mInvalid IP(s) detected: {invalid_ips}. Valid options are: {list(bias_map.keys())}.\033[0m")
        return

    # Apply bias settings for each selected IP
    for ip in selected_ips:
        full_ip = f"10.73.137.{100 + ip}"
        print(f"\033[32mSetting bias for IP {full_ip}\033[0m")

        try:
            # Initialize Daphne instance
            daphne = Daphne(full_ip)

            # Disable bias
            daphne.command(f'WR VBIASCTRL V {0}')
            print("Bias disabled.")

            # Set bias for each AFE
            for i, bias in enumerate(bias_map[ip]):
                daphne.command(f'WR BIASSET AFE {i} V {bias}')
                print(f"Set bias for AFE {i} to {bias} mV.")

            # Enable bias
            daphne.command(f'WR VBIASCTRL V {4000}')
            print("Bias enabled.")

            # Read and print bias voltages
            read_bias = daphne.read_bias()
            print(f"Bias voltages for {full_ip}:", read_bias)

            # Close the Daphne connection
            daphne.close()

        except Exception as e:
            print(f"\033[91mError while processing IP {full_ip}: {e}\033[0m")

if __name__ == "__main__":
    main()