import click
from ivtools import Daphne

@click.command()
@click.option("--ip_address", '-ip', default='ALL', help="Last digits of the IP address (comma-separated) or 'ALL'")
def main(ip_address):
    """
    Check configured timestamps for DAPHNE devices and validate consecutiveness.

    Args:
        - ip_address (default='ALL'): If 'ALL', runs on all predefined IPs.
                                     If digits, runs only on those endpoints.

    Example:
        python check_timestamp.py --ip_address 4,5
        python check_timestamp.py --ip_address ALL
    """
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RESET = "\033[0m"

    print(f"\033[35mExpecting: Consecutive timestamps (e.g., 108408431617009473, 108408431617009474) for each endpoint and none should be 0.\033[0m")

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

    # Check timestamps for each selected IP
    for ip in selected_ips:
        full_ip = f"10.73.137.{100 + ip}"
        print(f"\nChecking timestamp for endpoint {full_ip}")

        try:
            # Initialize Daphne instance
            interface = Daphne(full_ip)

            # Trigger spy buffers
            interface.write_reg(0x2000, [1234])

            # Read timestamp registers
            response = interface.read_reg(0x40500000, 4)

            # Extract timestamp values
            timestamps = response[2:]  # Skip metadata
            print(f"{GREEN}Timestamps: {timestamps}{RESET}")

            # Validate timestamps
            if any(ts == 0 for ts in timestamps):
                print(f"{RED}Warning: One or more timestamps are 0!{RESET}")
            elif all(timestamps[i + 1] - timestamps[i] == 1 for i in range(len(timestamps) - 1)):
                print(f"{GREEN}Timestamps are consecutive and valid.{RESET}")
            else:
                print(f"{YELLOW}Warning: Timestamps are not consecutive!{RESET}")

            # Close the interface
            interface.close()

        except Exception as e:
            print(f"{RED}Error while processing IP {full_ip}: {e}{RESET}")

if __name__ == "__main__":
    main()