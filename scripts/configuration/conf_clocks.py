import ivtools, click
from time import sleep

@click.command()
@click.option("--ip_address", '-ip', default='ALL',help="IP Address")
def main(ip_address):
    '''
    Choose whether we are running with local clocks or using the timing endpoint.
        
    Args: 
        - ip_address (default='ALL'): if no argument given it runs over all endpoints.
    
    Example: python conf_clocks.py (-ip 4,5)
    '''
    print(f"\033[35mExpecting: Error Count = 0 for all registers and the same DAPHNE firmaware version for all endpoints\033[0m")
    if ip_address=="ALL": your_ips = [4,5,10,9,11,12,13]
    else: your_ips = list(map(int, list(ip_address.split(","))))
    for ip in your_ips: 
        if ip not in [4,5,10,9,11,12,13]: 
            print("\033[91mInvalid IP address, please choose your ip between 4,5,10,9,11,12,13 :)\033[0m"); 
            exit()
        interface = ivtools.daphne(f'10.73.137.{100+ip}')
        print(f"\nConfiguring endpoint 10.73.137.{100+ip}")
        print("DAPHNE firmware version %0X" %interface.read_reg(0x9000,1)[2])
        USE_ENDPOINT = 1
        interface.write_reg(0x4001, [USE_ENDPOINT]) #Master Clock and Timing Endpoint Control Register (read write)
        interface.write_reg(0x4003, [1234])         #0x00004003  Write anything to reset timing endpoint
        sleep(0.5)
        interface.write_reg(0x4002, [1234])         #0x00004002  Write anything to reset master clock MMCM1
        sleep(0.5)
        interface.write_reg(0x2001, [1234])          
        sleep(0.5)
        print("AFE automatic alignment done, should read 0x1F: %0X" %interface.read_reg(0x2002,1)[2])
        print("AFE0 Error Count = %0X" % interface.read_reg(0x2010,1)[2])
        print("AFE1 Error Count = %0X" % interface.read_reg(0x2011,1)[2])
        print("AFE2 Error Count = %0X" % interface.read_reg(0x2012,1)[2])
        print("AFE3 Error Count = %0X" % interface.read_reg(0x2013,1)[2])
        print("AFE4 Error Count = %0X" % interface.read_reg(0x2014,1)[2])


if __name__ == "__main__":
    main()