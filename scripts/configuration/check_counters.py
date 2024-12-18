import click
from ivtools import Daphne

@click.command()
@click.option("--ip_address", '-ip', default='ALL', help="Last digits of the IP address (comma-separated) or 'ALL'")
def main(ip_address):
    """
    This script spies on the counters for each endpoint.

    Args:
        - ip_address (default='ALL'): If 'ALL', runs on all predefined IPs.
                                     If digits, runs only on those endpoints.

    Example:
        python check_counters.py --ip_address 4,5
        python check_counters.py --ip_address ALL
    """
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    MAGENTA = "\033[35m"
    WHITE = "\033[37m"
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

    # Spy on counters for each selected IP
    for ip in selected_ips:
        full_ip = f"10.73.137.{100 + ip}"
        print(f"{GREEN}Checking Counters for IP {full_ip}{RESET}")

        try:
            # Initialize Daphne instance
            interface = Daphne(full_ip)
            interface.write_reg(0x2001, [1234])  # Software trigger

            # Print headers
            print(f"{MAGENTA}ADDRESS{RESET}\t{MAGENTA}{full_ip}{RESET}")
            print(f"{WHITE}CH{RESET}\t{WHITE}TRIGGER{RESET}\t\t{WHITE}FIFO{RESET}\t\t{WHITE}FLX{RESET}")

            # Read counters
            trigger = [interface.read_reg(0x40800000 + n * 0x8, 1)[2] for n in range(40)]
            fifo = [interface.read_reg(0x40800140 + n * 0x8, 1)[2] for n in range(40)]
            flx = interface.read_reg(0x40800280, 1)[2]

            # Print counters
            for i in range(40):
                print(f"{WHITE}{i:02}{RESET}\t{GREEN}{trigger[i]:010}{RESET}\t{GREEN}{fifo[i]:010}{RESET}\t{YELLOW}{flx:010}{RESET}")

            # Close the interface
            interface.close()

        except Exception as e:
            print(f"{RED}Error while processing IP {full_ip}: {e}{RESET}")

if __name__ == "__main__":
    main()