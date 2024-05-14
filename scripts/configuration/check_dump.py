import ivtools, click

@click.command()
@click.option("--ip_address", '-ip', default='ALL',help="IP Address")
def main(ip_address):
    '''
    Args: 
        - ip_address (default='ALL'): if no argument given it runs over all endpoints.
    
    Example: python conf_clocks.py (-ip 4,5)
    '''
    
    print(f"\033[35mExpecting: Error Count = 0 for all registers and the same DAPHNE firmaware version for all endpoints\033[0m")
    if ip_address=="ALL": your_ips = [4,5,7,9,11,12,13]
    else: your_ips = list(map(int, list(ip_address.split(","))))
    for ip in your_ips: 
        if ip not in [4,5,7,9,11,12,13]: 
            print("\033[91mInvalid IP address, please choose your ip between 4,5,7,9,11,12,13 :)\033[0m"); 
            exit()
        interface = ivtools.daphne(f'10.73.137.{100+ip}')
        print(f"\nConfiguring endpoint 10.73.137.{100+ip}")

        print("DAPHNE firmware version %0X" % interface.read_reg(0x9000,1)[2])
        interface.write_reg(0x2000, [1234]) # software trigger, all spy buffers capture
        interface.write_reg(0x2001, [1234]) # software trigger, all spy buffers capture
        #thing.write(0x4002, [1234]) # software trigger, all spy buffers capture
        
        print

        for afe in range(5):
            for ch in range(9):
                print("AFE%d[%d]: " % (afe,ch),end="")
                for x in interface.read_reg(0x40000000+(afe*0x100000)+(ch*0x10000),15)[3:]:
                    print("%04X " % x,end="")
                print()
            print()

        interface.close()


if __name__ == "__main__":
    main()