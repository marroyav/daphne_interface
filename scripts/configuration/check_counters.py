import ivtools, click

@click.command()
@click.option("--ip_address", '-ip', default='ALL',help="IP Address")


def main(ip_address):
    '''
    This script spy on the counters for each endpoint.
    The expected output is:
        Checking Counters
        ADDRESS 10.73.137.112
        TRIGGER         FIFO            FLX
        0000000039      0000000015      0000001097
        0000000047      0000000014      0000001097
        0000000019      0000000015      0000001097
        0000000004      0000000014      0000001097
        0000000014      0000000016      0000001097
        0000000042      0000000016      0000001097
        
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

    if ip_address=="ALL": your_ips = [4,5,7,9,11,12,13]
    else: your_ips = your_ips = list(map(int, list(ip_address.split(","))))

    for ip in your_ips:
        if ip not in [4,5,7,9,11,12,13]: 
            print("\033[91mInvalid IP address, please choose your ip between 4,5,7,9,11,12,13 :)\033[0m"); 
            exit()
        interface = ivtools.daphne(f"10.73.137.{100+ip}")
        interface.write_reg(0x2001, [1234]) # software trigger, all spy buffers capture
        print (f"{BLUE}Checking Counters{RESET}")
        print (f"{BLUE}ADDRESS{RESET}",end='\t')
        print (f"{RED}10.73.137.{100+ip}{RESET}")
        print (f"{CYAN}CH{RESET}", end='\t')
        print (f"{CYAN}TRIGGER{RESET}", end='\t\t')
        print (f"{CYAN}FIFO{RESET}", end='\t\t')
        print (f"{CYAN}FLX{RESET}")
        trigger = [(interface.read_reg(0x40800000+n*0x8,1)[2]) for n in range(40)  ]
        fifo = [(interface.read_reg(0x40800140+n*0x8,1)[2]) for n in range(40)]
        flx = (interface.read_reg(0x40800280,1)[2])
        for i in range (40):
            print(f"{CYAN}{i:02}\t{GREEN}{trigger[i]:010}\t{GREEN}{fifo[i]:010}\t{YELLOW}{flx:010}{RESET}" )
        
        interface.close()


if __name__ == "__main__":
    main()
