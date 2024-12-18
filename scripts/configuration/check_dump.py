import click
from ivtools import Daphne

@click.command()
@click.option("--ip_address", '-ip', default='ALL', help="Last digits of the IP address (comma-separated) or 'ALL'")
def main(ip_address):
    """
    Checks DAPHNE AFE alignment for each endpoint.

    Args:
        - ip_address (default='ALL'): If 'ALL', runs on all predefined IPs.
                                     If digits, runs only on those endpoints.

    Example:
        python check_dump.py --ip_address 4,5
        python check_dump.py --ip_address ALL
    """
    RED = "\033[31m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"
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

    print(f"{MAGENTA}Expecting: Error Count = 0 for all registers and the same DAPHNE firmware version for all endpoints{RESET}")

    # CCheck Dump for each selected IP
    for ip in selected_ips:
        full_ip = f"10.73.137.{100 + ip}"
        try:
            # Initialize Daphne instance
            interface = Daphne(full_ip)
            print(f"\nConfiguring endpoint {full_ip}")

            # Read and print firmware version
            firmware_version = interface.read_reg(0x9000, 1)[2]
            print(f"DAPHNE firmware version {firmware_version:0X}")

            # Write configuration registers
            interface.write_reg(0x2000, [1234])  # Software trigger, all spy buffers capture
            interface.write_reg(0x2001, [1234])  # Software trigger, all spy buffers capture

            # Read and print register data
            for afe in range(5):
                for ch in range(9):
                    print(f"AFE{afe}[{ch}]: ", end="")
                    reg_data = interface.read_reg(0x40000000 + (afe * 0x100000) + (ch * 0x10000), 15)[3:]
                    for x in reg_data:
                        if ch == 8:
                            print(f"{RED}{x:04X}{RESET}", end=" ")
                        else:
                            print(f"{CYAN}{x:04X}{RESET}", end=" ")
                    print()
                print()

            # Close the interface
            interface.close()

        except Exception as e:
            print(f"{RED}Error while processing IP {full_ip}: {e}{RESET}")

if __name__ == "__main__":
    main()