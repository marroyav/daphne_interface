import ivtools, click

@click.command()
@click.option("--ip_address", '-ip', default='ALL',help="IP Address")
def main(ip_address):
    '''
    This script checks that the configured timestamp is OK.
    The expected output need to be different for each endpoint and there must be
    four consecutive prints of the form "107122026883802096".

    Args: 
        - ip_address (default='ALL'): if no argument given it runs over all endpoints.
    
    Example: python conf_analog.py (-ip 4,5)
    '''
    
    print(f"\033[35mExpecting: Different timestamp [i.e 107224329048024288] for each endpoints and different from 0\033[0m")

    if ip_address=="ALL": your_ips = [4,5,7,9,11,12,13]
    else: your_ips = your_ips = list(map(int, list(ip_address.split(","))))
    
    for ip in your_ips:
        if ip not in [4,5,7,9,11,12,13]: 
            print("\033[91mInvalid IP address, please choose your ip between 4,5,7,9,11,12,13 :)\033[0m"); 
            exit()
        interface = ivtools.daphne(f"10.73.137.{ip+100}")
        interface.write_reg(0x2000, [1234])
        print(f"\nChecking endpoint 10.73.137.{100+ip} time stamp in DAPHNE:")
        a = interface.read_reg(0x40500000,4)
        for r in range (len(a)-2):
            print (a[r+2])
        interface.close()


if __name__ == "__main__":
    main()