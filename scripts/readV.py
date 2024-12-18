import ivtools
import click


@click.command()
@click.option(
    "--facility", "-f",
    type=click.Choice(['np02', 'np04', 'vdcoldbox'], case_sensitive=False),
    help="Facility name (np02, np04, vdcoldbox)"
)
@click.option(
    "--ip_address", "-ip",
    default="ALL",
    help="IP Address (comma-separated or 'ALL')"
)
def main(facility, ip_address):
    """
    Reads and prints bias values for specified endpoints based on facility and IPs.
    """
    # Define IP sets for each facility
    facility_ips = {
        'np02': [7],
        'np04': [4, 9, 11, 12, 13],
        'vdcoldbox': [4, 5, 10],  # Add IPs for 'vdcoldbox' as needed
    }

    # Prompt for facility if not provided
    if not facility:
        facility = input(
            "Please specify the facility (np02, np04, vdcoldbox): "
        ).strip().lower()

    if facility not in facility_ips:
        print(
            f"\033[91mUnknown facility: {facility}. "
            "Please choose from np02, np04, or vdcoldbox.\033[0m"
        )
        exit()

    # Get allowed IPs for the chosen facility
    allowed_ips = facility_ips[facility]

    # Parse the provided IP addresses
    if ip_address == "ALL":
        your_ips = allowed_ips
        print(f"No IP specified, reading all endpoints for facility {facility.upper()}")
    else:
        your_ips = list(map(int, ip_address.split(",")))

    # Validate provided IPs
    for ip in your_ips:
        if ip not in allowed_ips:
            print(
                f"\033[91mInvalid IP address for {facility.upper()}. "
                f"Allowed IPs are: {allowed_ips}\033[0m"
            )
            exit()

    # Process each IP
    for ip in your_ips:
        daphne = ivtools.daphne(f"10.73.137.{100 + ip}")
        print("Bias for endpoint", ip, daphne.read_bias())
        daphne.close()


if __name__ == "__main__":
    main()
