import click
from tqdm import tqdm
from ivtools import Daphne
import re

@click.command()
@click.option("--ip_address", '-ip', default='ALL', help="Last digits of the IP address (comma-separated) or 'ALL'")
def main(ip_address):
    """
    Read analog chain for DAPHNE devices and parse responses into structured format.

    Args:
        - ip_address (default='ALL'): If 'ALL', runs on all predefined IPs.
                                     If digits, runs only on those endpoints.

    Example:
        python check_analog.py --ip_address 4,5
        python check_analog.py --ip_address ALL
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

    # Read parameters for each selected IP
    for ip in selected_ips:
        full_ip = f"10.73.137.{100 + ip}"
        print(f"{GREEN}Configuring Offset in 40-ch DAPHNE {100 + ip}{RESET}")

        try:
            # Initialize Daphne instance
            interface = Daphne(full_ip)


            # Parse channel responses
            channels_data = []
            print(f"Reading channels for {full_ip}")
            for ch in tqdm(range(40), desc=f"Reading channels for {full_ip}", unit="Channels"):
                response = interface.command(f'RD OFFSET CH {ch}')
                match = re.search(r'OFFSET DAC REG= (\d+).*DAC GAIN=(\d+)', response)
                if match:
                    dac_reg, dac_gain = map(int, match.groups())
                    channels_data.append({'Channel': ch, 'DAC_REG': dac_reg, 'DAC_GAIN': dac_gain})
            
            print(f"\n{CYAN}Channels Data:{RESET}")
            for ch_data in channels_data:
                print(f"Channel {ch_data['Channel']:02}: OFFSET={ch_data['DAC_REG']}, DAC_GAIN={ch_data['DAC_GAIN']}")

            # Parse AFE responses
            afes_data = []
            print(f"\n{GREEN}Reading AFE registers and attenuators for {full_ip}{RESET}")
            for afe in tqdm(range(5), desc=f"Reading AFEs for {full_ip}", unit="AFE"):
                afe_data = {'AFE': afe}
                for reg in [52, 4, 51]:
                    response = interface.command(f'RD AFE {afe} REG {reg}')
                    match = re.search(r'CMD Read AFE\d+ REG\d+ = (\d+)', response)
                    if match:
                        afe_data[f'REG_{reg}'] = int(match.group(1))

                response = interface.command(f'RD AFE {afe} VGAIN')
                match = re.search(r'VGAIN DAC REG= (\d+).*DAC GAIN=(\d+)', response)
                if match:
                    afe_data['VGAIN_REG'], afe_data['VGAIN_GAIN'] = map(int, match.groups())
                
                afes_data.append(afe_data)

            print(f"\n{CYAN}AFEs Data:{RESET}")
            for afe_data in afes_data:
                print(f"AFE {afe_data['AFE']:d}: REG_52={afe_data.get('REG_52', 'N/A')}, "
                      f"REG_4={afe_data.get('REG_4', 'N/A')}, REG_51={afe_data.get('REG_51', 'N/A')}, "
                      f"VGAIN_REG={afe_data.get('VGAIN_REG', 'N/A')}, VGAIN_GAIN={afe_data.get('VGAIN_GAIN', 'N/A')}")

            print(f"\n{GREEN}Finished reading parameters for {full_ip}.{RESET}")

            # Close the interface
            interface.close()

        except Exception as e:
            print(f"{RED}Error while processing IP {full_ip}: {e}{RESET}")

if __name__ == "__main__":
    main()