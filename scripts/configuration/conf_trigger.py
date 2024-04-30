import ivtools, click, warnings

@click.command()
@click.option("--ip_address", '-ip', default='ALL',help="IP Address")
def main(ip_address):
    '''
    This script only configure the full-streaming endpoints [4,5,7].
        
    Args: 
        - ip_address (default='ALL'): if no argument given it runs over all endpoints.
        If any of the given endpoint is not expected to be full-streaming a warning 
        will appear and the loop will continue with the next element.
    
    Example: python conf_datamodes.py (-ip 4,5)
    '''
    if ip_address=="ALL": your_ips = [4,5,7] #Only full-streaming endpoints
    else: your_ips = your_ips = list(map(int, list(ip_address.split(","))))
    for ip in your_ips: 
        if ip not in [4,5,7,9,11,12,13]: 
            print("\033[91mInvalid IP address, please choose your ip between 4,5,7,9,11,12,13 :)\033[0m"); 
            exit()
            
        if ip in [9,11,12,13]: 
            warnings.warn(f'EndPoint {ip} not full-streaming (expecting 4,5 or 7), continuing with the next one...')
            continue

        ip=f'10.73.137.{100+ip}'
        interface = ivtools.daphne(ip)
        configure = False
        interface.write_reg(0x2000,[1234]) #Write anything to trigger spybuffers
        reg = 0x5000
        
        if configure: print(f'--- Configuring ip {ip} ---')
        else:         print(f'--- Reading configuration ip {ip} ---')
        
        if ip==4:
            for k in range (2):
                for j in [0,2,5,7,1,3,4,6]:
                    if configure:
                        interface.write_reg(reg, [10*k+j])
                    print(hex(reg), end=' = ')
                    print(f'{interface.read_reg(reg,1)[2]}')
                    reg = reg+1
        elif ip==5:
            for k in range(1):
                for j in [0,2,5,7,1,3,4,6]:
                    if configure:
                        interface.write_reg(reg, [10*k+j])
                    print(hex(reg), end=' = ')
                    print(f'{interface.read_reg(reg,1)[2]}')
                    reg = reg+1
            for k in [1]:
                for j in [0,2,5,7]:
                    if configure:
                        interface.write_reg(reg, [10*k+j])
                    print(hex(reg), end=' = ')
                    print(f'{interface.read_reg(reg,1)[2]}')
                    reg = reg+1
            for k in [2]:
                for j in [1,3,4,6]:
                    if configure:
                        interface.write_reg(reg, [10*k+j])
                    print(hex(reg), end=' = ')
                    print(f'{interface.read_reg(reg,1)[2]}')
                    reg = reg+1
        else:
            for k in [0]:
                for j in [0,2,5,7]:
                    if configure:
                        interface.write_reg(reg, [10*k+j])
                    print(hex(reg), end=' = ')
                    print (f'{interface.read_reg(reg,1)[2]}')
                    reg=reg+1
            for k in [1]:
                for j in [0,2,5,7]: 
                    if configure:
                        interface.write_reg(reg, [10*k+j])
                    print(hex(reg), end=' = ')
                    print(f'{interface.read_reg(reg,1)[2]}')
                    reg=reg+1
            for k in [2]:
                for j in range(0,8):
                    if configure:
                        interface.write_reg(reg, [8])
                    print(hex(reg), end=' = ')
                    print(f'{interface.read_reg(reg,1)[2]}')
                    reg = reg+1

        interface.close()


if __name__ == "__main__":
    main()