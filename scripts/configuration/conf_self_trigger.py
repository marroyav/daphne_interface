import click
from ivtools import Daphne


@click.command()
@click.option("--ip_address", '-ip', default='ALL', help="Last digits of the IP address (comma-separated) or 'ALL'")
def main(ip_address):
    """
    Configure the self-trigger module for DAPHNE: Match Filter.

    Args:
        - ip_address (default='ALL'): If 'ALL', runs on all predefined IPs.
                                     If digits, runs only on those endpoints.

    Example:
        python conf_self_trigger.py --ip_address 4,9
        python conf_self_trigger.py --ip_address ALL
    """
    RED = "\033[31m"
    GREEN = "\033[32m"
    RESET = "\033[0m"

    print(f"{GREEN}Configuring self-trigger module for selected DAPHNE endpoints.{RESET}")

    # Predefined valid IPs
    valid_ips = [4,7, 9, 11, 12, 13, 6]

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

    # Configure each selected IP
    for ip in selected_ips:
        full_ip = f"10.73.137.{100 + ip}"
        print(f"\nConfiguring endpoint {full_ip}")

        try:
            # Initialize Daphne instance
            interface = Daphne(full_ip)

            # Read firmware version
            firmware_version = interface.read_reg(0x9000, 1)[2]
            print(f"DAPHNE firmware version: {GREEN}{firmware_version:08X}{RESET}")

            # Read match filter configuration
            match_filter_config = interface.read_reg(0x6100, 1)[2]
            print(f"Match Filter Configuration: {GREEN}{match_filter_config:08X}{RESET}")

            # Uncomment the following lines to write configurations if needed
            # Configure self-trigger
            interface.write_reg(0x6100, [0x20010000032])  # Self-trigger ~1.5pe 450adu xcorr
            interface.write_reg(0x6002, [0xe935])         # Configure primitive module ~1.5pe
            interface.write_reg(0x6001, [0xFFFFFFFFFF])   # Enable self-trigger for all channels
            # interface.write_reg(0x2023, [0x0])            # Selector for half of the channels on the APA

            # Readback configurations
            # print(f"Primitive Module Configuration: {GREEN}{interface.read_reg(0x6002, 1)[2]:08X}{RESET}")
            # print(f"Detector Side: {GREEN}{interface.read_reg(0x2023, 1)[2]:08X}{RESET}")
            # print(f"Channels Enabled: {GREEN}{interface.read_reg(0x6001, 1)[2]:08X}{RESET}")
            # print(f"APA Side: {GREEN}{interface.read_reg(0x2023, 1)[2]:08X}{RESET}")

            # Close the interface
            interface.close()

        except Exception as e:
            print(f"{RED}Error while processing IP {full_ip}: {e}{RESET}")


if __name__ == "__main__":
    main()
