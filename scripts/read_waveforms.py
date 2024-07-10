import ivtools, click

@click.command()
@click.option("--ip_address", '-ip', default='ALL',help="IP Address")
def main(ip_address):
    '''
    This script checks that the data output in DAPHNE is OK.
    The expected output are chucks of data with the structure of the frames configured in data modes.
    Self triggered endpoints might print an undeterministic ammount of waveforms since those will have many IDLEs
    If you arrange the terminal in columns multiples of 7 you can see the pattern 

    Args: 
        - ip_address (default='ALL'): if no argument given it runs over all endpoints.
    
    Example: python conf_analog.py (-ip 4,5)
    '''
    
    print(f"\033[35mExpecting: Different waveforms\033[0m")

    if ip_address=="ALL": your_ips = [4,5,7,9,11,12,13]
    else: your_ips = your_ips = list(map(int, list(ip_address.split(","))))

    for ip in your_ips:
        if ip not in [4,5,7,9,11,12,13]: 
            print("\033[91mInvalid IP address, please choose your ip between 40 :)\033[0m"); 
            exit()
        interface = ivtools.daphne(f"10.73.137.{100+ip}")
        interface.write_reg(0x2000, [1234])
        rec=[]
        print(f"\033[91m\nChecking ip address 10.73.137.{ip+100} data out in DAPHNE:\033[0m")
        print()
        for i in range (10):
            doutrec = interface.read_reg(0x40600000+i*128,128)
            for word in doutrec[2:]:
                rec.append(word)

        for i in range (len(rec)):
            if rec[i] == 0x000000BC:
                if rec[i-1] == 0x000000BC:
                    pass
                else:
                    print(f"\033[36m{rec[i]:08X}\033[0m")
            elif rec[i] == 0xFFFFFFFF:
                print(f"\033[31m{rec[i]:08X}\033[0m",end=' ')
            elif rec[i] == 0xDEADBEEF:
                print(f"\033[33m{rec[i]:08X}\033[0m",end=' ')
            elif rec[i] == 0x0000003C:
                print(f"\033[32m{rec[i]:08X}\033[0m")
            else:
                if rec[i-1] == 0x0000003C:
                    print(f"\033[33m{rec[i]:08X}\033[0m",end=' ')
                else:
                    print(f"{rec[i]:08X}",end=' ')
    interface.close()

if __name__ == "__main__":
    main()
