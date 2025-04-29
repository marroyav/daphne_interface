import click
from tqdm import tqdm
from ivtools import Daphne

@click.command()
@click.option("--ip_address", '-ip', required=True, help="Last digits of the IP address")
@click.option("--offsets", '-o', required=True, help="Comma-separated list of exactly 5 offset values for groups of 8 channels")
def set_offsets(ip_address, offsets):
    """
    Set offset values for groups of 8 channels (total 40 channels) on a specific DAPHNE device.

    Args:
        ip_address: Last digits of the IP address.
        offsets: Comma-separated list of exactly 5 offset values, each applied to 8 channels.

    Example:
        python set_offsets.py --ip_address 4 --offsets 2250,2300,2200,2150,2100
    """
    RED = "\033[31m"
    GREEN = "\033[32m"
    RESET = "\033[0m"

    offset_values = list(map(int, offsets.split(',')))

    if len(offset_values) != 5:
        print(f"{RED}Error: Exactly 5 offset values are required for 5 groups of 8 channels.{RESET}")
        return

    full_ip = f"10.73.137.{100 + int(ip_address)}"
    print(f"{GREEN}Configuring Offset for DAPHNE {100 + int(ip_address)} at {full_ip}{RESET}")

    try:
        interface = Daphne(full_ip)

        for group_idx, offset in enumerate(tqdm(offset_values, total=5, desc="Setting offsets for groups", unit="Groups")):
            for ch in range(group_idx * 8, (group_idx + 1) * 8):
                interface.command(f'WR OFFSET CH {ch} V {offset}')

        print(f"{GREEN}Offsets successfully updated for {full_ip}.{RESET}")

        interface.close()

    except Exception as e:
        print(f"{RED}Error while configuring IP {full_ip}: {e}{RESET}")

if __name__ == "__main__":
    set_offsets()