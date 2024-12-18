import click
from warnings import warn
from ivtools import Daphne


@click.command()
@click.option("--ip_address", '-ip', default='ALL', help="Last digits of the IP address (comma-separated) or 'ALL'")
def main(ip_address):
    """
    Configure or read settings for full-streaming DAPHNE endpoints.

    Args:
        - ip_address (default='ALL'): If 'ALL', runs on all predefined full-streaming endpoints.
                                     If digits, runs only on those endpoints.

    Example:
        python conf_full_stream.py --ip_address 4,5
        python conf_full_stream.py --ip_address ALL
    """
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RESET = "\033[0m"

    # Predefined valid full-streaming endpoints
    full_stream_ips = [4, 5, 7]
    all_valid_ips = [4, 5, 10, 9, 11, 12, 13, 7, 6]

    # Process input argument
    if ip_address.upper() == "ALL":
        selected_ips = full_stream_ips
    else:
        try:
            selected_ips = list(map(int, ip_address.split(",")))
        except ValueError:
            print(f"{RED}Invalid IP address input. Use 'ALL' or comma-separated numbers.{RESET}")
            return

    # Validate selected IPs
    invalid_ips = [ip for ip in selected_ips if ip not in all_valid_ips]
    if invalid_ips:
        print(f"{RED}Invalid IP(s) detected: {invalid_ips}. Valid options are: {all_valid_ips}.{RESET}")
        return

    # Configure or read for each selected IP
    for ip in selected_ips:
        if ip not in full_stream_ips:
            warn(f"{YELLOW}EndPoint {ip} is not a full-streaming endpoint (expected 4, 5, or 7). Skipping.{RESET}")
            continue

        full_ip = f"10.73.137.{100 + ip}"
        print(f"\n--- Processing endpoint {full_ip} ---")

        try:
            # Initialize Daphne instance
            interface = Daphne(full_ip)
            configure = False  # Change to True for configuration mode
            reg = 0x5000

            if configure:
                print(f"{GREEN}Configuring endpoint {full_ip}.{RESET}")
            else:
                print(f"{YELLOW}Reading configuration for endpoint {full_ip}.{RESET}")

            # Handle configurations or readings for specific IPs
            if ip == 4:
                process_endpoint_4(interface, reg, configure)
            elif ip == 5:
                process_endpoint_5(interface, reg, configure)
            elif ip == 7:
                process_endpoint_7(interface, reg, configure)

            # Close the interface
            interface.close()

        except Exception as e:
            print(f"{RED}Error while processing IP {full_ip}: {e}{RESET}")


def process_endpoint_4(interface, reg, configure):
    """Process configuration or readings for endpoint 4."""
    for k in range(2):
        for j in [0, 2, 5, 7, 1, 3, 4, 6]:
            handle_register(interface, reg, k, j, configure)
            reg += 1


def process_endpoint_5(interface, reg, configure):
    """Process configuration or readings for endpoint 5."""
    for k in range(1):
        for j in [0, 2, 5, 7, 1, 3, 4, 6]:
            handle_register(interface, reg, k, j, configure)
            reg += 1
    for k in [1]:
        for j in [0, 2, 5, 7]:
            handle_register(interface, reg, k, j, configure)
            reg += 1
    for k in [2]:
        for j in [1, 3, 4, 6]:
            handle_register(interface, reg, k, j, configure)
            reg += 1


def process_endpoint_7(interface, reg, configure):
    """Process configuration or readings for endpoint 7."""
    for k in [0, 1]:
        for j in [0, 2, 5, 7]:
            handle_register(interface, reg, k, j, configure)
            reg += 1
    for k in [2]:
        for j in range(8):
            handle_register(interface, reg, k, j, configure, value=8)
            reg += 1


def handle_register(interface, reg, k, j, configure, value=None):
    """Handle a single register configuration or read operation."""
    if configure:
        value_to_write = value if value is not None else 10 * k + j
        interface.write_reg(reg, [value_to_write])
    print(f"{hex(reg)} = {interface.read_reg(reg, 1)[2]}")


if __name__ == "__main__":
    main()