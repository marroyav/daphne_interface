import click
from ivtools import Daphne

@click.command()
@click.option("--ip_address", '-ip', default='ALL', help="Last digits of the IP address (comma-separated) or 'ALL'")
def main(ip_address):
    """
    This script checks that the data output in DAPHNE is OK.
    The expected output are chunks of data with the structure of the frames configured in data modes.
    Self-triggered endpoints might print an undeterministic amount of waveforms due to many IDLEs.
    If you arrange the terminal in columns multiples of 7, you can see the pattern.

    Args:
        - ip_address (default='ALL'): If 'ALL', runs on all predefined endpoints.
                                     If digits, runs only on those endpoints.

    Example:
        python check_data_output.py --ip_address 4,5
        python check_data_output.py --ip_address ALL
    """
    RED = "\033[31m"
    GREEN = "\033[32m"
    BLUE = "\033[36m"
    YELLOW = "\033[33m"
    MAGENTA = "\033[35m"
    RESET = "\033[0m"

    print(f"{MAGENTA}Expecting: Different waveforms{RESET}")

    # Predefined valid IPs
    valid_ips = [4, 5, 7, 10, 9, 11, 12, 13]

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

    # Check data output for each selected IP
    for ip in selected_ips:
        full_ip = f"10.73.137.{100 + ip}"
        print(f"\n{RED}Checking IP address {full_ip} data out in DAPHNE:{RESET}\n")

        try:
            # Initialize Daphne instance
            interface = Daphne(full_ip)
            interface.write_reg(0x2000, [1234])  # Trigger spy buffers
            rec = []

            # Read data from the registers
            for i in range(10):
                doutrec = interface.read_reg(0x40600000 + i * 128, 128)
                rec.extend(doutrec[2:])  # Skip metadata

            # Print formatted data output
            print_formatted_output(rec)

            # Close the interface
            interface.close()

        except Exception as e:
            print(f"{RED}Error while processing IP {full_ip}: {e}{RESET}")


def print_formatted_output(data):
    """
    Print formatted output for the given data.

    Args:
        - data: List of integers representing data output.
    """
    BLUE = "\033[36m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    GREEN = "\033[32m"
    RESET = "\033[0m"

    for i, word in enumerate(data):
        if word == 0x000000BC:
            if i > 0 and data[i - 1] != 0x000000BC:
                print(f"{BLUE}{word:08X}{RESET}")
        elif word == 0xFFFFFFFF:
            print(f"{RED}{word:08X}{RESET}", end=' ')
        elif word == 0xDEADBEEF:
            print(f"{YELLOW}{word:08X}{RESET}", end=' ')
        elif word == 0x0000003C:
            print(f"{GREEN}{word:08X}{RESET}")
        else:
            if i > 0 and data[i - 1] == 0x0000003C:
                print(f"{YELLOW}{word:08X}{RESET}", end=' ')
            else:
                print(f"{word:08X}", end=' ')


if __name__ == "__main__":
    main()