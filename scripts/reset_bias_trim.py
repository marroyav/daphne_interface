import ivtools, click

@click.command()
@click.option("--ip_address", '-ip', default='ALL',help="IP Address")
def main(ip_address):
    if ip_address=="ALL": your_ips = [4,5,7,9,11,12,13]
    else: your_ips = your_ips = list(map(int, list(ip_address.split(","))))

    for ip in your_ips:
        if ip not in [4,5,7,9,11,12,13]: 
            print("\033[91mInvalid IP address, please choose your ip between 4,5,7,9,11,12,13 :)\033[0m"); 
            exit()

        daphne = ivtools.daphne(f"10.73.137.{100+ip}")
        disable_bias = daphne.command('WR VBIASCTRL V 0')
        reset_bias = [daphne.command(f'WR BIASSET AFE {i} V 0') for i in range(5)]
        # reset_trim = [daphne.command(f'WR TRIM CH {i} V 0') for i in range(40)]
        print("Bias for endpoint",ip,daphne.read_bias())
        daphne.close()

if __name__ == "__main__":
    main()