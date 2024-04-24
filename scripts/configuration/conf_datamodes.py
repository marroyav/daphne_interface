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
                 11:["hi_rate_self_trigger", 0x002081], #
                 12:["hi_rate_self_trigger", 0x002081], #
                 13:["hi_rate_self_trigger", 0x002081]  #
                 }
    
    for ip in your_ips: 
        interface = ivtools.daphne(f"10.73.137.{100+ip}")
        print(f"address= 10.73.137.{100+ip}")
        trigger = data_mode[ip][0]
        d0x3000 = data_mode[ip][1]

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
            interface.write_reg(0x6000,[16000])
            print(f"threshhold = {interface.read_reg(0x6000,1)[2]}")
            interface.write_reg(0x6001,[0xfffffffff])
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