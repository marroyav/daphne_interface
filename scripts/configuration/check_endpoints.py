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
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    RESET = "\033[0m"

    print(f"\033[35mExpecting: The same firmware version and a Good to go!!! message for all endpoints\033[0m")

    if ip_address=="ALL": your_ips = [4,5,10,9,11,12,13]
    else: your_ips = your_ips = list(map(int, list(ip_address.split(","))))
    for ip in your_ips:
        if ip not in [4,5,10,9,11,12,13]: 
            print("\033[91mInvalid IP address, please choose your ip between 4,5,10,9,11,12,13:)\033[0m"); 
            exit()
        ip = f"10.73.137.{100+ip}"
        interface = ivtools.daphne(ip)
        print(f"\n--------------------------------------")
        print(f"--------------------------------------")
        print(f"DAPHNE ip address {ip}")
        print(f"DAPHNE firmware version\t{YELLOW}{interface.read_reg(0x9000,1)[2]:08x}{RESET}")
        print(f"test resgisters\t\t{interface.read_reg(0xaa55,1)[2]:08x}")
        print(f"endpoint address\t{interface.read_reg(0x4001,1)[2]:08x}")
        print(f"register 5001\t\t{interface.read_reg(0x5001,1)[2]:08x}")
        print(f"register 3000\t\t{interface.read_reg(0x3000,1)[2]:08x}")

        epstat = interface.read_reg(0x4000,1)[2] # read_reg the timing endpoint and master cl    ock status register

        if (epstat & 0x00000001):
                print(f"{GREEN}MMCM0 is LOCKED OK{RESET}")
        else:
                print(f"{YELLOW}Warning! MMCM0 is UNLOCKED, need a hard reset!{RESET}")

        if (epstat & 0x00000002):
                print(f"{GREEN}Master clock MMCM1 is LOCKED OK{RESET}")
        else:
                print(f"{YELLOW}Warning! Master clock MMCM1 is UNLOCKED!{RESET}")

        if (epstat & 0x00000010):
                print(f"{YELLOW}Warning! CDR chip loss of signal (LOS=1){RESET}")
        else:
                print(f"{GREEN}CDR chip signal OK (LOS=0){RESET}")

        if (epstat & 0x00000020):
                print(f"{YELLOW}Warning! CDR chip UNLOCKED (LOL=1){RESET}")
        else:
                print(f"{GREEN}CDR chip LOCKED (LOL=0) OK{RESET}")

        if (epstat & 0x00000040):
                print(f"{YELLOW}Warning! Timing SFP module optical loss of signal (LOS=1){RESET}"    )
        else:
                print(f"{GREEN}Timing SFP module optical signal OK (LOS=0){RESET}")

        if (epstat & 0x00000080):
                print(f"{YELLOW}Warning! Timing SFP module NOT DETECTED!{RESET}")
        else:
                print(f"{GREEN}Timing SFP module is present OK{RESET}")

        if (epstat & 0x00001000):
                print(f"{GREEN}Timing endpoint timestamp is valid{RESET}")
        else:
                print(f"{YELLOW}Warning! Timing endpoint timestamp is NOT valid{RESET}")
        ep_state = (epstat & 0xF00) >> 8  # timing endpoint state bits

        if ep_state==0:
                print(f"{RED}Endpoint State = 0 : Starting state after reset{RESET}")
        elif ep_state==1:
                print(f"{RED}Endpoint State = 1 : Waiting for SFP LOS to go low{RESET}")
        elif ep_state==2:
                print(f"{RED}Endpoint State = 2 : Waiting for good frequency check{RESET}")
        elif ep_state==3:
                print(f"{RED}Endpoint State = 3 : Waiting for phase adjustment to complete{RESET}")
        elif ep_state==4:
                print(f"{RED}Endpoint State = 4 : Waiting for comma alignment, stable 62.5MHz phase{RESET}")
        elif ep_state==5:
                print(f"{RED}Endpoint State = 5 : Waiting for 8b10 decoder good packet{RESET}")
        elif ep_state==6:
                print(f"{RED}Endpoint State = 6 : Waiting for phase adjustment command{RESET}")
        elif ep_state==7:
                print(f"{RED}Endpoint State = 7 : Waiting for time stamp initialization{RESET}")
        elif ep_state==8:
                print(f"{GREEN}Endpoint State = 8 : Good to go!!!{RESET}")
        elif ep_state==12:
                print(f"{RED}Endpoint State = 12 : Error in rx{RESET}")
        elif ep_state==13:
                print(f"{RED}Endpoint State = 13 : Error in time stamp check{RESET}")
        elif ep_state==14:
                print(f"{RED}Endpoint State = 14 : Physical layer error after lock{RESET}")
        else:
                print(f"{YELLOW}Endpoint State = {ep_state} : warning! undefined state!{RESET}")

        interface.close()


if __name__ == "__main__":
    main()