import ivtools, click

@click.command()
@click.option("--ip_address", '-ip', default='ALL',help="IP Address")
def main(ip_address):
    '''
    Configure in DAPHNE the data modes for each endpoint:
        - 104, 105, 107 are expected in self-trigger (0x3) 
        - 109, 111, 112, 113 are expected in full streaming (0xAA)
    Set output record parameters  (0x3000)
    Set thresholds (self-trigger) (0x6000)
    
    Args: 
        - ip_address (default='ALL'): if no argument given it runs over all endpoints.
    
    Example: python conf_datamodes.py (-ip 4,5)
    '''
    
    if ip_address=="ALL": your_ips = [4,5,7,9,11,12,13]
    else: your_ips = your_ips = list(map(int, list(ip_address.split(","))))

    data_mode = {4: ["full_stream", 0x001081],          # 
                 5: ["full_stream", 0x001081],          #
                 7: ["full_stream", 0x001081],          #
                 9: ["hi_rate_self_trigger", 0x001081], #
                 11:["hi_rate_self_trigger", 0x002081,0xffffffffff], #
                 12:["hi_rate_self_trigger", 0x002081,0x25ffffffff], #
                 13:["hi_rate_self_trigger", 0x002081,0xa5]  #
                 }
    print(f"\033[35mExpecting: The same parameters output (Crate number) for all endpoints\033[0m")
    
    threshold = input(f"\nFor this script you need to specify your threshold [CALIB: 9000, COMIC: 600]:  ")
    threshold = int(threshold)

    for ip in your_ips: 
        if ip not in [4,5,7,9,11,12,13]: 
            print("\033[91mInvalid IP address, please choose your ip between 4,5,7,9,11,12,13 :)\033[0m"); 
            exit()
        interface = ivtools.daphne(f"10.73.137.{100+ip}")
        print(f"\nConfiguring endpoint 10.73.137.{100+ip}")
        trigger = data_mode[ip][0] # trigger mode
        d0x3000 = data_mode[ip][1] #
        d0x6001 = data_mode[ip][2] #40 channels register that configures what channels are being saved

        if trigger == "full_stream":
            interface.write_reg(0x3000,[d0x3000+ip*0x400000])
            print(f"parameters =  {hex(interface.read_reg(0x3000,1)[2])}")
            interface.write_reg(0x3001,[0xaa])
            print(f"data mode = {hex(interface.read_reg(0x3001,1)[2])}")
            interface.write_reg(0x6001,[0b00000000])
            print(f"channels active = {interface.read_reg(0x6001,1)[2]}")
            print(f"reg 0x5007 = {(interface.read_reg(0x5007,2))}")

            interface.close()
        
        if trigger == "hi_rate_self_trigger":
            interface.write_reg(0x3000,[d0x3000+ip*0x400000])
            print(f"parameters =  {hex(interface.read_reg(0x3000,1)[2])}")
            interface.write_reg(0x3001,[0x3])
            print(f"data mode = {hex(interface.read_reg(0x3001,1)[2])}")
            interface.write_reg(0x6000,[threshold])  # Setting threshold [ADC counts] with user input
            print(f"threshhold = {interface.read_reg(0x6000,1)[2]}")
            interface.write_reg(0x6001,[d0x6001]) # Setting channels to make trigger with map information
            #Avoid matching-trigger #commenting this line will enable matching trigger
            # if ip==11: 
            #     ## Daniel Avila self-trigger
            #     print(f"[daniel] Special endpoint {ip}")
            #     interface.write_reg(0x6001,[0x0000A50000])
                # interface.write_reg(0x6100,[0x3FCE0000190]) 
            ## disenable :0x3FB03FFFFFF
            ## ~50 ADC counts threshold: 0x3FCE000012C
            ## >60 ADC counts threshold: 0x3FCE0000190
            # if ip==12:
            #     print(f"[daniel] Special endpoint {ip}")
            #     # print(f"[nacho] Special endpoint {ip}")
            #     interface.write_reg(0x6001,[0xA500000000])
            #     interface.write_reg(0x6100,[0x3FCE0000190])
            #     # interface.write_reg(0x7001,[0x3E55])   # Threshold=-4, slope with 3 samples
            #     # interface.write_reg(0x7001,[0x3DD5]) # Threshold=-5, slope with 3 samples
            #     # interface.write_reg(0x7001,[0x3E15]) # Threshold=-4, slope with 2 samples
            # if ip==13:
            #     interface.write_reg(0x6001,[0x0000000A5])

            print(f"channels active = {interface.read_reg(0x6001,1)[2]}")
        
        if trigger == "low_rate_self_trigger":
            interface.write_reg(0x3000,[d0x3000+ip*0x400000])
            print(f"parameters =  {hex(interface.read_reg(0x3000,1)[2])}")
            interface.write_reg(0x3001,[0x3])
            print(f"data mode = {hex(interface.read_reg(0x3001,1)[2])}")
            interface.write_reg(0x6000,[30])
            print(f"threshhold = {interface.read_reg(0x6000,1)[2]}")
            interface.write_reg(0x6001,[0b0])
            print(f"channels active = {interface.read_reg(0x6001,1)[2]}")

        if trigger == "disable":
            interface.write_reg(0x3000,[d0x3000+ip*0x400000])
            print(f"parameters =  {hex(interface.read_reg(0x3000,1)[2])}")
            interface.write_reg(0x3001,[0x0])
            print(f"data mode = {hex(interface.read_reg(0x3001,1)[2])}")
            interface.write_reg(0x6001,[0b00000000])
            print(f"channels active = {interface.read_reg(0x6001,1)[2]}")

            interface.close()


if __name__ == "__main__":
    main()