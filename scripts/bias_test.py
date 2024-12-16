import ivtools, click

# List of bias vectors to iterate over
BIAS_VECTORS = [
  #  [806, 0, 1200, 0, 0],
  #  [793, 0, 1187, 0, 0],
  #  [780, 0, 1174, 0, 0],
    [767, 0, 1161, 0, 0],
    [767, 0, 1161, 0, 0],
    [767, 0, 1161, 0, 0]]
  #  [754, 0, 1148, 0, 0] ]

@click.command()
@click.option("--ip_address", '-ip', default='6', help="IP Address (default: 6)")
def main(ip_address):
    # Validate IP address
    if ip_address != "6":
        print("\033[91mInvalid IP address! Only endpoint 6 is supported.\033[0m")
        return

    ip = "10.73.137.106"
    print(f"Configuring endpoint {ip} for multiple bias vectors...")
    interface = ivtools.daphne(ip)

    # Iterate over each bias vector
    for idx, voltages in enumerate(BIAS_VECTORS, start=1):
        print(f"Applying Bias Vector {idx}: {voltages}")
        try:
            # Disable bias
            interface.command('WR VBIASCTRL V 0')

            # Apply the voltages
            for channel, voltage in enumerate(voltages):
                interface.command(f'WR BIASSET AFE {channel} V {voltage}')

            for i in range (10):
                print("Applied Bias:", interface.read_bias())
            # Enable bias
            interface.command('WR VBIASCTRL V 4095')

            # Confirm and print the applied bias
            print("Applied Bias:", interface.read_bias())
        except Exception as e:
            print(f"\033[91mError applying Bias Vector {idx}: {e}\033[0m")
            continue  # Proceed to the next vector if there's an error


if __name__ == "__main__":
    main()
