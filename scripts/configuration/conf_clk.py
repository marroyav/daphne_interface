import ivtools
import argparse
from time import sleep


class config(object):
    def __init__(self,ip_address):
        self.device = ivtools.daphne(ip_address)
        print("DAPHNE firmware version %0X" % self.device.read_reg(0x9000,1)[2])
        USE_ENDPOINT = 1
        EDGE_SELECT = 0
        TIMING_GROUP = 0
        ENDPOINT_ADDRESS = 0
        self.device.write_reg(0x4001, [USE_ENDPOINT])
        self.device.write_reg(0x3001, [0b11111111])
        self.device.write_reg(0x4003, [1234])
        sleep(0.5)
        self.device.write_reg(0x4002, [1234])
        sleep(0.5)
        self.device.write_reg(0x2001, [1234])
        sleep(0.5)
        print("AFE automatic alignment done, should read 0x1F: %0X" % self.device.read_reg(0x2002,1)[2])
        print("AFE0 Error Count = %0X" % self.device.read_reg(0x2010,1)[2])
        print("AFE1 Error Count = %0X" % self.device.read_reg(0x2011,1)[2])
        print("AFE2 Error Count = %0X" % self.device.read_reg(0x2012,1)[2])
        print("AFE3 Error Count = %0X" % self.device.read_reg(0x2013,1)[2])
        print("AFE4 Error Count = %0X" % self.device.read_reg(0x2014,1)[2])
        print("Crate number = %0X" % self.device.read_reg(0x3000,1)[2])

def main():
    parser = argparse.ArgumentParser(description="Initial configuration of DAPHNE")
    parser.add_argument('--ip', type=str, required=False, help='IP address.')
    args=parser.parse_args()
    if args.ip:
        c=config(args.ip)
    else:
        for i in [4,5,7,9,11,12,13]:
            c=config(f"10.73.137.{100+i}")



if __name__ == "__main__":
    main()

