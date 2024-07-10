import ivtools, click

@click.command()
@click.option("--ip_address", '-ip', default='ALL',help="IP Address")
def main(ip_address):
    '''
    This script checks the datamode for each endpoint configured with conf_datamodes.py.
    The expected output is:
        DAPHNE physical scheme
        ADDRESS         SLOT    REG     MODE
        10.73.137.104   4       0xaa    full streaming
        10.73.137.105   5       0xaa    full streaming
        10.73.137.107   7       0xaa    full streaming
        10.73.137.109   9       0x3     self trigger
        10.73.137.111   11      0x3     self trigger
        10.73.137.112   12      0x3     self trigger
        10.73.137.113   13      0x3     self trigger
        
    Args: 
        - ip_address (default='ALL'): if no argument given it runs over all endpoints.
    
    Example: python conf_analog.py (-ip 4,5)
    '''
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    RESET = "\033[0m"
    print ("DAPHNE physical scheme")
    print ("ADDRESS", end='\t\t')
    print ("SLOT", end='\t')
    print ("REG", end='\t')
    print ("MODE")

    if ip_address=="ALL": your_ips = [4,5,7,9,11,12,13]
    else: your_ips = your_ips = list(map(int, list(ip_address.split(","))))

    for ip in your_ips:
        if ip not in [4,5,7,9,11,12,13]: 
            print("\033[91mInvalid IP address, please choose your ip between 4,5,7,9,11,12,13 :)\033[0m"); 
            exit()
        interface = ivtools.daphne(f"10.73.137.{100+ip}")
        print(f"10.73.137.{100+ip}",end='\t')
        slot = (interface.read_reg(0x3000,1)[2]>>22)
        sender = (interface.read_reg(0x3001,1)[2])
        
        print(f"{slot}",end='\t')
        print(f"{hex(sender)}",end='\t')

        if   sender==0xaa: print(f"{CYAN}full streaming{RESET}")
        elif sender==0x3:  print(f"{GREEN}self trigger{RESET}")
        else:              print(f"{RED}disabled{RESET}")
        
        interface.close()


if __name__ == "__main__":
    main()