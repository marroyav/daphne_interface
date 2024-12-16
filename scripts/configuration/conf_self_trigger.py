import ivtools, click
from time import sleep

@click.command()
@click.option("--ip_address", '-ip', default='ALL',help="IP Address")
def main(ip_address):
    '''
    Choose the apropriate configuration for the self trigger module in DAPHNE:match filter

    Args:
        - ip_address (default='ALL'): if no argument given it runs over all endpoints.

    Example: python conf_clocks.py (-ip 4,5)
    '''
    if ip_address=="ALL": your_ips = [4,9,11,12,13,6,6,6,6]
    else: your_ips = list(map(int, list(ip_address.split(","))))
    for ip in your_ips:
        if ip not in [4,9,11,12,13,6,6,6,6]:
            print("\033[91mInvalid IP address, please choose your ip between 4,5,10,9,11,12,13,6 :)\033[0m");
            exit()
        interface = ivtools.daphne(f'10.73.137.{100+ip}')
        print(f"\nConfiguring endpoint 10.73.137.{100+ip}")
        print("DAPHNE firmware version %0X" %interface.read_reg(0x9000,1)[2])
        #interface.write_reg(0x6100,[0x020010000064])  # configures the self trigger at ~1.5pe 450adu xcorr
        interface.write_reg(0x6002, [0xF137])         # configuresthe primitive module at ~1.5pe
        #interface.write_reg(0x6001, [0xffffffffff])   # self trigger enable for all channels
        #interface.write_reg(0x2023, [0x0])            # selector of half of the channels on the APA
        print("Match filter Configuration= %0X" %interface.read_reg(0x6100,1)[2])  # configures the self trigger at ~1.5pe 450adu xcorr
        print("Primitives module Configuration= %0X" %interface.read_reg(0x6002,1)[2])
        print("Detector side= %0X" % interface.read_reg(0x2023, 1)[2])
        #print("Channels Enabled= %0X" % interface.write_reg(0x6001, 1)[2])   # self trigger enable for all channels
        #print("APA side= %0X" % interface.write_reg(0x2023, 1)[2])            # selector of half of the channels on the APA


if __name__ == "__main__":
    main()
