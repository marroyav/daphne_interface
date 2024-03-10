import ivtools
import argparse
from time import sleep


class config(object):
    def __init__(self,ip_address):
        self.device = ivtools.oei.OEI(ip_address)
        print("DAPHNE firmware version %0X" % self.device.read_reg(0x9000,1)[2])
        # master clock input can be endpoint (=1) or local clocks (=0), choose that here:
        USE_ENDPOINT = 1
        # configure these misc timing endpoint parameters
        EDGE_SELECT = 0
        TIMING_GROUP = 0
        ENDPOINT_ADDRESS = 0
        # now write to the master clock and endpoint control register:
        #temp = (ENDPOINT_ADDRESS&0xFF)<<8 + (TIMING_GROUP&0x3)<<2 + (EDGE_SELECT&0x1)<<1 + (USE_ENDPOINT & 0x1)
        self.device.write_reg(0x4001, [USE_ENDPOINT])
        self.device.write_reg(0x3000, [0x002081+(0x400000*int(ip_address[-1]))])
        self.device.write_reg(0x3001, [0b11111111])
        # now reset the timing endpoint logic
        self.device.write_reg(0x4003, [1234])
        # wait a moment for timing endpoint clocks to stabilize...
        sleep(0.5)
        # reset the master clock MMCM1
        self.device.write_reg(0x4002, [1234])
        # wait a moment for the master clocks to stabilize...
        sleep(0.5)
        # reset the front end and force recalibration
        self.device.write_reg(0x2001, [1234])
        # wait a moment for the front end logic to recalibrate...
        sleep(0.5)
        # dump out front end status registers...
        # 5 LSb's = DONE bits should be HIGH if the front end has completed auto alignment
        print("AFE automatic alignment done, should read 0x1F: %0X" % self.device.read_reg(0x2002,1)[2])
        # bit error count registers for each AFE
        # if an error is observed on the "FCLK" pattern it increments this counter up to 0xFF
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
        #for i in [12]:
        for i in [13]:
            c=config(f"10.73.137.{100+i}")



if __name__ == "__main__":
    main()

