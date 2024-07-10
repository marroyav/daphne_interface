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

    if ip_address=="ALL": your_ips = [4,5,7,9,11,12,13]
    else: your_ips = your_ips = list(map(int, list(ip_address.split(","))))

    for ip in your_ips:
        if ip not in [4,5,7,9,11,12,13]: 
            print("\033[91mInvalid IP address, please choose your ip between 4,5,7,9,11,12,13 :)\033[0m"); 
            exit()
        interface = ivtools.daphne(f"10.73.137.{100+ip}")
        interface.write_reg(0x2001, [1234]) # software trigger, all spy buffers capture
        print ("Checking Counters")
        print ("ADDRESS",end='\t')
        print (f"10.73.137.{100+ip}")
        print ("TRIGGER", end='\t\t\t')
        print ("FIFO", end='\t\t')
        print ("FLX")
        trigger = [(interface.read_reg(0x40800000+n*0x8,1)[2]) for n in range(40)  ]
        fifo = [(interface.read_reg(0x40800140+n*0x8,1)[2]) for n in range(40)]
        flx = (interface.read_reg(0x40800280,1)[2])
        for i in range (40):
            print(f"{trigger[i]}",end='\t'),print(f"{fifo[i]}",end='\t'),print(f"{flx}",end='\t'),print()
        
        interface.close()


if __name__ == "__main__":
    main()
