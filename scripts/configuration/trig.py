import ivtools

for i in [4,5,7]:
    ip=f'10.73.137.{100+i}'
    interface = ivtools.daphne(ip)
    configure = False
    interface.write_reg(0x2000,[1234])
    reg=0x5000
    if configure: 
        print (f'configuring ip {ip}')
    else:
        print (f'reading configuration ip {ip}')
    if i == 4:
        for k in range (2):
            for j in [0,2,5,7,1,3,4,6]:
                if configure:
                    interface.write_reg(reg, [10*k+j])
                print(hex(reg), end=' = ')
                print (f'{interface.read_reg(reg,1)[2]}')
                reg=reg+1
    elif i==5:
        for k in range(1):
            for j in [0,2,5,7,1,3,4,6]:
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
                print (f'{interface.read_reg(reg,1)[2]}')
                reg=reg+1
        for k in [2]:
            for j in [1,3,4,6]:
                if configure:
                    interface.write_reg(reg, [10*k+j])
                print(hex(reg), end=' = ')
                print (f'{interface.read_reg(reg,1)[2]}')
                reg=reg+1
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
                print (f'{interface.read_reg(reg,1)[2]}')
                reg=reg+1
        for k in [2]:
            for j in range(0,8):
                if configure:
                    interface.write_reg(reg, [8])
                print(hex(reg), end=' = ')
                print (f'{interface.read_reg(reg,1)[2]}')
                reg=reg+1
    interface.close()