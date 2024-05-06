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

    if ip_address=="ALL": your_ips = [4,5,7,9,11,12,13]
    else: your_ips = your_ips = list(map(int, list(ip_address.split(","))))
    
    for ip in your_ips: 
        if ip not in [4,5,7,9,11,12,13]: 
            print("\033[91mInvalid IP address, please choose your ip between 4,5,7,9,11,12,13 :)\033[0m"); 
            exit()   
        interface = ivtools.daphne(f'10.73.137.{100+ip}')
        print(f'Configuring Offset in 40 ch DAPHNE {100+ip} ')
        interface.command( f'CFG AFE ALL INITIAL')
        for ch in tqdm(range(40),unit='Channels'):
            interface.command('WR OFFSET CH '  + str(int(ch)) + ' V 1100')
            interface.command('CFG OFFSET CH ' + str(int(ch)) + ' GAIN 2')

        print(f'Configuring AFE registers 4, 51, 52 and Attenuators')
        for AFE in tqdm(range(5),unit='AFE'):
            interface.command('WR AFE '+ str(int(AFE)) + ' REG 52 V 16896')
            interface.command('WR AFE '+ str(int(AFE)) + ' REG 4 V 24')
            interface.command('WR AFE '+ str(int(AFE)) + ' REG 51 V 0')
            interface.command('WR AFE '+ str(int(AFE)) + ' VGAIN V 2318')
            alignment=[interface.write_reg(0x2001,[1234]) for _ in range (3)]
        print('Finished writing commands.')
        interface.close()


if __name__ == "__main__":
    main()