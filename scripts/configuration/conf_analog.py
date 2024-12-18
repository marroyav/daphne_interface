import click
from tqdm import tqdm
from ivtools import Daphne

@click.command()
@click.option("--ip_address", '-ip', default='ALL', help="Last digits of the IP address (comma-separated) or 'ALL'")
def main(ip_address):
    """
    Set output record parameters (0x3000) for DAPHNE devices.

    Args:
        - ip_address (default='ALL'): If 'ALL', runs on all predefined IPs.
                                     If digits, runs only on those endpoints.

    Example:
        python conf_analog.py --ip_address 4,5
        python conf_analog.py --ip_address ALL
    """
    RED = "\033[31m"
    GREEN = "\033[32m"
    RESET = "\033[0m"

    # Predefined valid IPs
    valid_ips = [4, 5, 10, 9, 11, 12, 13, 7, 6]

    # Process input argument
    if ip_address.upper() == "ALL":
        selected_ips = valid_ips
    else:
        try:
            selected_ips = list(map(int, ip_address.split(",")))
        except ValueError:
            print(f"{RED}Invalid IP address input. Use 'ALL' or comma-separated numbers.{RESET}")
            return

    # Validate selected IPs
    invalid_ips = [ip for ip in selected_ips if ip not in valid_ips]
    if invalid_ips:
        print(f"{RED}Invalid IP(s) detected: {invalid_ips}. Valid options are: {valid_ips}.{RESET}")
        return

    # Configure parameters for each selected IP
    for ip in selected_ips:
        full_ip = f"10.73.137.{100 + ip}"
        print(f"{GREEN}Configuring Offset in 40-ch DAPHNE {100 + ip}{RESET}")

        try:
            # Initialize Daphne instance
            interface = Daphne(full_ip)

            # Configure AFE ALL INITIAL
            interface.command('CFG AFE ALL INITIAL')

            # Configure offset for all 40 channels
            for ch in tqdm(range(40), desc=f"Configuring channels for {full_ip}", unit="Channels"):
                interface.command(f'WR OFFSET CH {ch} V 2250')
                interface.command(f'CFG OFFSET CH {ch} GAIN 1')

            # Configure AFE registers and attenuators
            print(f"{GREEN}Configuring AFE registers 4, 51, 52 and Attenuators{RESET}")
            for afe in tqdm(range(5), desc=f"Configuring AFEs for {full_ip}", unit="AFE"):
                interface.command(f'WR AFE {afe} REG 52 V 20480')
                interface.command(f'WR AFE {afe} REG 4 V 24')
                interface.command(f'WR AFE {afe} REG 51 V 16')
                interface.command(f'WR AFE {afe} VGAIN V 1000')

                # Alignment writes
                for _ in range(3):
                    interface.write_reg(0x2001, [1234])

            print(f"{GREEN}Finished writing commands for {full_ip}.{RESET}")

            # Close the interface
            interface.close()

        except Exception as e:
            print(f"{RED}Error while processing IP {full_ip}: {e}{RESET}")

if __name__ == "__main__":
    main()