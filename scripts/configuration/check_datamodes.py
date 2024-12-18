import click
from ivtools import Daphne

@click.command()
@click.option("--ip_address", '-ip', default='ALL', help="Last digits of the IP address (comma-separated) or 'ALL'")
def main(ip_address):
    """
    This script checks the data mode for each endpoint configured with `conf_datamodes.py`.

    Args:
        - ip_address (default='ALL'): If 'ALL', runs on all predefined IPs.
                                     If digits, runs only on those endpoints.

    Example:
        python check_datamode.py --ip_address 4,5
        python check_datamode.py --ip_address ALL
    """
    RED = "\033[31m"
    GREEN = "\033[32m"
    CYAN = "\033[36m"
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

    # Print header
    print("DAPHNE physical scheme")
    print("ADDRESS", end='\t\t')
    print("SLOT", end='\t')
    print("REG", end='\t')
    print("MODE")

    # Check data mode for each selected IP
    for ip in selected_ips:
        full_ip = f"10.73.137.{100 + ip}"
        try:
            # Initialize Daphne instance
            interface = Daphne(full_ip)
            print(f"{full_ip}", end='\t')

            # Read slot and sender mode
            slot = (interface.read_reg(0x3000, 1)[2] >> 22)
            sender = (interface.read_reg(0x3001, 1)[2])

            # Print slot and sender register
            print(f"{slot}", end='\t')
            print(f"{hex(sender)}", end='\t')

            # Determine mode
            if sender == 0xaa:
                print(f"{CYAN}full streaming{RESET}")
            elif sender == 0x3:
                print(f"{GREEN}self trigger{RESET}")
            else:
                print(f"{RED}disabled{RESET}")

            # Close the interface
            interface.close()

        except Exception as e:
            print(f"{RED}Error while processing IP {full_ip}: {e}{RESET}")

if __name__ == "__main__":
    main()