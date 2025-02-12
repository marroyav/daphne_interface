import click
from ivtools import Daphne

@click.command()
@click.option("--ip_address", '-ip', default='ALL', help="Last digits of the IP address (comma-separated) or 'ALL'")
def main(ip_address):
    """
    Configure DAPHNE data modes for endpoints.

    Args:
        - ip_address (default='ALL'): If 'ALL', runs on all predefined IPs.
                                     If digits, runs only on those endpoints.

    Example:
        python conf_datamodes.py --ip_address 4,5
        python conf_datamodes.py --ip_address ALL
    """
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RESET = "\033[0m"

    print(f"{GREEN}Configuring data modes for selected DAPHNE endpoints.{RESET}")

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

    # Data mode configuration
    data_mode = {
        4: ["full_stream", 0x001081, 0xFFFF],
        5: ["full_stream", 0x001081, 0x5A0A5FF],
        7: ["full_stream", 0x001081, 0x8040201FF],  # Channels for endpoint 7
        9: ["hi_rate_self_trigger", 0x001081, 0xFFFFFFFFFF],
        11: ["hi_rate_self_trigger", 0x002081, 0xFFFFFFFFFF],
        12: ["hi_rate_self_trigger", 0x002081, 0xA5FFFFFFFF],
        13: ["hi_rate_self_trigger", 0x002081, 0xA5],
    }

    # Threshold input
    try:
        threshold = int(input(f"{YELLOW}Enter threshold [CALIB: 9000, COMIC: 600]: {RESET}"))
    except ValueError:
        print(f"{RED}Invalid threshold input. Please enter a numeric value.{RESET}")
        return

    # Configure each selected IP
    for ip in selected_ips:
        full_ip = f"10.73.137.{100 + ip}"
        print(f"\nConfiguring endpoint {full_ip}")

        try:
            # Initialize Daphne instance
            interface = Daphne(full_ip)

            # Retrieve data mode details
            trigger, d0x3000, d0x6001 = data_mode[ip]

            if trigger == "full_stream":
                configure_full_stream(interface, ip, d0x3000, d0x6001)

            elif trigger == "hi_rate_self_trigger":
                configure_hi_rate_self_trigger(interface, ip, d0x3000, d0x6001, threshold)

            # Special configuration for endpoint 7
            #if ip == 7:
            #    configure_channels(interface, [0, 7, 8, 15, 16, 23, 24, 31, 32,33,34,35,36,37,38,39])

            interface.close()

        except Exception as e:
            print(f"{RED}Error while processing IP {full_ip}: {e}{RESET}")


def configure_full_stream(interface, ip, d0x3000, d0x6001):
    """Configure full stream mode."""
    GREEN = "\033[32m"
    RESET = "\033[0m"

    interface.write_reg(0x3000, [d0x3000 + ip * 0x400000])
    print(f"Parameters: {GREEN}{hex(interface.read_reg(0x3000, 1)[2])}{RESET}")

    interface.write_reg(0x3001, [0xAA])
    print(f"Data mode: {GREEN}{hex(interface.read_reg(0x3001, 1)[2])}{RESET}")

    interface.write_reg(0x6001, [d0x6001])
    print(f"Channels active: {GREEN}{hex(interface.read_reg(0x6001, 1)[2])}{RESET}")


def configure_hi_rate_self_trigger(interface, ip, d0x3000, d0x6001, threshold):
    """Configure high-rate self-trigger mode."""
    GREEN = "\033[32m"
    RESET = "\033[0m"

    interface.write_reg(0x3000, [d0x3000 + ip * 0x400000])
    print(f"Parameters: {GREEN}{hex(interface.read_reg(0x3000, 1)[2])}{RESET}")

    interface.write_reg(0x3001, [0x3])
    print(f"Data mode: {GREEN}{hex(interface.read_reg(0x3001, 1)[2])}{RESET}")

    interface.write_reg(0x6000, [threshold])
    print(f"Threshold: {GREEN}{interface.read_reg(0x6000, 1)[2]}{RESET}")

    interface.write_reg(0x6001, [d0x6001])
    print(f"Channels active: {GREEN}{hex(interface.read_reg(0x6001, 1)[2])}{RESET}")


def configure_channels(interface, channels):
    """Configure specific channels for endpoint 7."""
    GREEN = "\033[32m"
    RESET = "\033[0m"

    # Convert channel list to 40-bit register value
    register_value = sum(1 << ch for ch in channels)
    interface.write_reg(0x1018, [register_value])
    print(f"Channel configuration (0x1018): {GREEN}{bin(register_value)}{RESET}")


if __name__ == "__main__":
    main()
