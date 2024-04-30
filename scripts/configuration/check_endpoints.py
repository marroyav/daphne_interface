import ivtools, click

@click.command()
@click.option("--ip_address", '-ip', default='ALL',help="IP Address")
def main(ip_address):
    '''
    Verify the clocks and timing endpoint is in a good state (registers 0x4000, 0x4002, 0x4003)
    This script checks the status of the yellow fiber connecting to the timing interface.
    We expect a "Good to go!" message, if not we should run: source setup_timing.sh (from np04daq@np04-srv-024 daphne/config/ folder)
    
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
        ip = f"10.73.137.{100+ip}"
        interface = ivtools.daphne(ip)
        print(f"--------------------------------------")
        print(f"--------------------------------------")
        print(f"DAPHNE ip address {ip}")
        print("DAPHNE firmware version %0X" % interface.read_reg(0x9000,1)[2])
        print("test resgisters %0X" % interface.read_reg(0xaa55,1)[2])
        print("endpoint address %0X" % interface.read_reg(0x4001,1)[2])
        print("register 5001 %0X" % interface.read_reg(0x5001,1)[2])
        print("register 3000 %0X" % interface.read_reg(0x3000,1)[2])

        epstat = interface.read_reg(0x4000,1)[2] # read_reg the timing endpoint and master cl    ock status register

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

        interface.close()


if __name__ == "__main__":
    main()