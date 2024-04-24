import ivtools
import argparse

class config(object):
    def __init__(self,ip_address):

        thing = ivtools.daphne(ip_address)
        print(f"--------------------------------------")
        print(f"--------------------------------------")
        print(f"DAPHNE ip address {ip_address}")
        print("DAPHNE firmware version %0X" % thing.read_reg(0x9000,1)[2])
        print("test resgisters %0X" % thing.read_reg(0xaa55,1)[2])
        print("endpoint address %0X" % thing.read_reg(0x4001,1)[2])
        print("register 5001 %0X" % thing.read_reg(0x5001,1)[2])
        print("register 3000 %0X" % thing.read_reg(0x3000,1)[2])

        epstat = thing.read_reg(0x4000,1)[2] # read_reg the timing endpoint and master cl    ock status register

        if (epstat & 0x00000001):
                print("MMCM0 is LOCKED OK")
        else:
                print("Warning! MMCM0 is UNLOCKED, need a hard reset!")

        if (epstat & 0x00000002):
                print("Master clock MMCM1 is LOCKED OK")
        else:
                print("Warning! Master clock MMCM1 is UNLOCKED!")

        if (epstat & 0x00000010):
                print("Warning! CDR chip loss of signal (LOS=1)")
        else:
                print("CDR chip signal OK (LOS=0)")

        if (epstat & 0x00000020):
                print("Warning! CDR chip UNLOCKED (LOL=1)")
        else:
                print("CDR chip LOCKED (LOL=0) OK")

        if (epstat & 0x00000040):
                print("Warning! Timing SFP module optical loss of signal (LOS=1)"    )
        else:
                print("Timing SFP module optical signal OK (LOS=0)")

        if (epstat & 0x00000080):
                print("Warning! Timing SFP module NOT DETECTED!")
        else:
                print("Timing SFP module is present OK")

        if (epstat & 0x00001000):
                print("Timing endpoint timestamp is valid")
        else:
                print("Warning! Timing endpoint timestamp is NOT valid")
        ep_state = (epstat & 0xF00) >> 8  # timing endpoint state bits

        if ep_state==0:
                print("Endpoint State = 0 : Starting state after reset")
        elif ep_state==1:
                print("Endpoint State = 1 : Waiting for SFP LOS to go low")
        elif ep_state==2:
                print("Endpoint State = 2 : Waiting for good frequency check")
        elif ep_state==3:
                print("Endpoint State = 3 : Waiting for phase adjustment to complete")
        elif ep_state==4:
                print("Endpoint State = 4 : Waiting for comma alignment, stable 62.5MHz phase")
        elif ep_state==5:
                print("Endpoint State = 5 : Waiting for 8b10 decoder good packet")
        elif ep_state==6:
                print("Endpoint State = 6 : Waiting for phase adjustment command")
        elif ep_state==7:
                print("Endpoint State = 7 : Waiting for time stamp initialization")
        elif ep_state==8:
                print("Endpoint State = 8 : Good to go!!!")
        elif ep_state==12:
                print("Endpoint State = 12 : Error in rx")
        elif ep_state==13:
                print("Endpoint State = 13 : Error in time stamp check")
        elif ep_state==14:
                print("Endpoint State = 14 : Physical layer error after lock")
        else:
                print("Endpoint State = %d : warning! undefined state!" %ep_state)

        thing.close()

def main():
    parser = argparse.ArgumentParser(description="Endpoint Status of DAPHNE")
    parser.add_argument('--ip', type=str, required=False, help='IP address.')
    args=parser.parse_args()
    if args.ip:
        c=config(args.ip)
    else:
        for i in [4,5,7,9,11,12,13]:
            c=config(f"10.73.137.{100+i}")



if __name__ == "__main__":
    main()
                       