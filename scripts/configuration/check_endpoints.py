import click
from ivtools import Daphne

@click.command()
@click.option("--ip_address", '-ip', default='ALL', help="Last digits of the IP address (comma-separated) or 'ALL'")
def main(ip_address):
    """
    Verify the clocks and timing endpoint for DAPHNE devices.

    Args:
        - ip_address (default='ALL'): If 'ALL', runs on all predefined IPs.
                                     If digits, runs only on those endpoints.

    Example:
        python verify_clocks.py --ip_address 4,5
        python verify_clocks.py --ip_address ALL
    """
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RESET = "\033[0m"

    print(f"\033[35mExpecting: The same firmware version and a Good to go!!! message for all endpoints\033[0m")

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

    # Verify clocks and timing endpoints for each selected IP
    for ip in selected_ips:
        full_ip = f"10.73.137.{100 + ip}"
        print(f"\n--------------------------------------")
        print(f"Checking DAPHNE device at {full_ip}")

        try:
            # Initialize Daphne instance
            interface = Daphne(full_ip)

            # Read firmware version
            firmware_version = interface.read_reg(0x9000, 1)[2]
            print(f"DAPHNE firmware version\t{YELLOW}{firmware_version:08x}{RESET}")

            # Read and display register values
            registers = {
                "test_registers": interface.read_reg(0xaa55, 1)[2],
                "endpoint_address": interface.read_reg(0x4001, 1)[2],
                "register_5001": interface.read_reg(0x5001, 1)[2],
                "register_3000": interface.read_reg(0x3000, 1)[2],
            }
            for reg, value in registers.items():
                print(f"{reg.replace('_', ' ')}\t{value:08x}")

            # Read endpoint status
            epstat = interface.read_reg(0x4000, 1)[2]

            # Interpret MMCM and clock status
            mmcm_status = [
                ("MMCM0 LOCKED", epstat & 0x00000001),
                ("Master clock MMCM1 LOCKED", epstat & 0x00000002),
                ("CDR chip signal OK (LOS=0)", not (epstat & 0x00000010)),
                ("CDR chip LOCKED (LOL=0)", not (epstat & 0x00000020)),
                ("Timing SFP module optical signal OK (LOS=0)", not (epstat & 0x00000040)),
                ("Timing SFP module is present", not (epstat & 0x00000080)),
                ("Timing endpoint timestamp valid", epstat & 0x00001000),
            ]
            for name, status in mmcm_status:
                color = GREEN if status else YELLOW
                print(f"{color}{name} {RESET if status else 'Warning!'}")

            # Interpret endpoint state
            ep_state = (epstat & 0xF00) >> 8
            state_messages = {
                0: f"{RED}Starting state after reset{RESET}",
                1: f"{RED}Waiting for SFP LOS to go low{RESET}",
                2: f"{RED}Waiting for good frequency check{RESET}",
                3: f"{RED}Waiting for phase adjustment to complete{RESET}",
                4: f"{RED}Waiting for comma alignment, stable 62.5MHz phase{RESET}",
                5: f"{RED}Waiting for 8b10 decoder good packet{RESET}",
                6: f"{RED}Waiting for phase adjustment command{RESET}",
                7: f"{RED}Waiting for time stamp initialization{RESET}",
                8: f"{GREEN}Good to go!!!{RESET}",
                12: f"{RED}Error in rx{RESET}",
                13: f"{RED}Error in time stamp check{RESET}",
                14: f"{RED}Physical layer error after lock{RESET}",
            }
            print(state_messages.get(ep_state, f"{YELLOW}Warning! Undefined state {ep_state}.{RESET}"))

            # Close the interface
            interface.close()

        except Exception as e:
            print(f"{RED}Error while processing IP {full_ip}: {e}{RESET}")

if __name__ == "__main__":
    main()