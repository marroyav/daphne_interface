import click
from ivtools import Daphne
from time import sleep

@click.command()
@click.option("--ip_address", '-ip', default='ALL', help="Last digits of the IP address (comma-separated) or 'ALL'")
def main(ip_address):
    """
    Configure DAPHNE endpoints to use local clocks or the timing endpoint.

    Args:
        - ip_address (default='ALL'): If 'ALL', runs on all predefined IPs.
                                     If digits, runs only on those endpoints.

    Example:
        python configure_clocks.py --ip_address 4,5
        python configure_clocks.py --ip_address ALL
    """
    RED = "\033[31m"
    GREEN = "\033[32m"
    RESET = "\033[0m"

    print(f"{GREEN}Expecting: Error Count = 0 for all registers and the same DAPHNE firmware version for all endpoints.{RESET}")

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

    # Configure each selected IP
    for ip in selected_ips:
        full_ip = f"10.73.137.{100 + ip}"
        print(f"\nConfiguring endpoint {full_ip}")

        try:
            # Initialize Daphne instance
            interface = Daphne(full_ip)

            # Read and display firmware version
            firmware_version = interface.read_reg(0x9000, 1)[2]
            print(f"DAPHNE firmware version: {GREEN}{firmware_version:08X}{RESET}")

            # Configure timing and clocks
            USE_ENDPOINT = 0
            interface.write_reg(0x4001, [USE_ENDPOINT])  # Master Clock and Timing Endpoint Control Register
            interface.write_reg(0x4003, [1234])          # Reset timing endpoint
            sleep(0.5)
            interface.write_reg(0x4002, [1234])          # Reset master clock MMCM1
            sleep(0.5)
            interface.write_reg(0x2001, [1234])          # AFE automatic alignment
            sleep(0.5)

            # Read alignment and error counts
            alignment_status = interface.read_reg(0x2002, 1)[2]
            mclk_state = interface.read_reg(0x4000,1)[2]
            print(f"AFE automatic alignment done, should read 0x1F: {GREEN}{alignment_status:02X}{RESET}")
            print(f"MCLK state: {GREEN}{bin(mclk_state)[2:]}{RESET}")
            for afe in range(5):
                error_count = interface.read_reg(0x2010 + afe, 1)[2]
                if error_count == 0:
                    print(f"AFE{afe} Error Count: {GREEN}{error_count:02X}{RESET}")
                else:
                    print(f"AFE{afe} Error Count: {RED}{error_count:02X}{RESET}")

            # Close the interface
            interface.close()

        except Exception as e:
            print(f"{RED}Error while processing IP {full_ip}: {e}{RESET}")

if __name__ == "__main__":
    main()
