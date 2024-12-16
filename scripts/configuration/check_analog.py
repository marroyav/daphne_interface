import ivtools, click
from tqdm import tqdm

@click.command()
@click.option("--ip_address", '-ip', default='ALL',help="IP Address")
def main(ip_address):
    '''
    Set output record parameters (0x3000)

    Args:
        - ip_address (default='ALL'): if no argument given it runs over all endpoints.

    Example: python conf_analog.py (-ip 4,5)
    '''

    if ip_address=="ALL": your_ips = [4,9,11,12,13,6]
    else: your_ips = your_ips = list(map(int, list(ip_address.split(","))))

    for ip in your_ips:
        if ip not in [4,9,11,12,13,6]:
            print("\033[91mInvalid IP address, please choose your ip between 4,5,7,9,11,12,13 :)\033[0m");
            exit()
        interface = ivtools.daphne(f'10.73.137.{100+ip}')
        print(f'Checking Offset in 40 ch DAPHNE {100+ip} ')
        for ch in tqdm([0,2,5,7,8,10,13,14],unit='Channels'):
            print(interface.command('RD OFFSET CH '  + str(int(ch))))

        print(f'Configuring AFE registers 4, 51, 52 and Attenuators')
        for AFE in tqdm(range(5),unit='AFE'):
            print(interface.command('RD AFE '+ str(int(AFE)) + ' REG 52'))
            print(interface.command('RD AFE '+ str(int(AFE)) + ' REG 4'))
            print(interface.command('RD AFE '+ str(int(AFE)) + ' REG 51'))
            print(interface.command('RD AFE '+ str(int(AFE)) + ' VGAIN'))
        print('Finished reading regs.')
        interface.close()


if __name__ == "__main__":
    main()
