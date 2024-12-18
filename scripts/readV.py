import ivtools
import click
from tabulate import tabulate

@click.command()
@click.option(
    "--facility", "-f",
    default="np02",
    type=click.Choice(['np02', 'np04', 'vdcoldbox'], case_sensitive=False),
    help="Facility name (default: np02)"
)
@click.option(
    "--ip_address", "-ip",
    default="ALL",
    help="IP Address (comma-separated or 'ALL')"
)
def main(facility, ip_address):
    """
    Reads and displays bias voltages, power readings, and temperature
    for specified endpoints in a tabular format.
    """
    RED = "\033[91m"
    GREEN = "\033[32m"
    RESET = "\033[0m"

    # Define IP sets for each facility
    facility_ips = {
        'np02': [7],
        'np04': [4, 9, 11, 12, 13],
        'vdcoldbox': [4, 5, 10],
    }

    # Validate facility
    if facility not in facility_ips:
        print(f"{RED}Unknown facility: {facility}. Please choose from np02, np04, or vdcoldbox.{RESET}")
        exit()

    # Get allowed IPs for the chosen facility
    allowed_ips = facility_ips[facility]

    # Parse the provided IP addresses
    if ip_address.upper() == "ALL":
        your_ips = allowed_ips
        print(f"{GREEN}No IP specified, reading all endpoints for facility {facility.upper()}.{RESET}")
    else:
        try:
            your_ips = list(map(int, ip_address.split(",")))
        except ValueError:
            print(f"{RED}Invalid IP address input. Use 'ALL' or a comma-separated list of numbers.{RESET}")
            exit()

    # Validate provided IPs
    invalid_ips = [ip for ip in your_ips if ip not in allowed_ips]
    if invalid_ips:
        print(f"{RED}Invalid IP(s) for {facility.upper()}: {invalid_ips}. Allowed IPs are: {allowed_ips}{RESET}")
        exit()

    # Read and display data
    headers = ["IP Address", "VBIAS0", "VBIAS1", "VBIAS2", "VBIAS3", "VBIAS4", "POWER(-5V)", "POWER(+2.5V)", "POWER(+CE)", "TEMP (°C)"]
    table = []

    for ip in your_ips:
        full_ip = f"10.73.137.{100 + ip}"
        print(f"\n{GREEN}Reading bias for endpoint {full_ip}:{RESET}")
        try:
            daphne = ivtools.Daphne(full_ip)
            variables = daphne.read_bias()

            # Prepare row for the table
            row = [
                full_ip,
                variables.get("VBIAS0", "N/A"),
                variables.get("VBIAS1", "N/A"),
                variables.get("VBIAS2", "N/A"),
                variables.get("VBIAS3", "N/A"),
                variables.get("VBIAS4", "N/A"),
                variables.get("POWER(-5v)", "N/A"),
                variables.get("POWER(+2.5v)", "N/A"),
                variables.get("POWER(+CE)", "N/A"),
                variables.get("TEMP(Celsius)", "N/A"),
            ]
            table.append(row)

            daphne.close()
        except Exception as e:
            print(f"{RED}Error while reading bias for endpoint {full_ip}: {e}{RESET}")

    # Display the table
    print(tabulate(table, headers=headers, tablefmt="fancy_grid"))


if __name__ == "__main__":
    main()