import ivtools
import multiprocessing
from time import sleep
from tqdm import tqdm

def configure(ep):
    ip=f'10.73.137.{100+ep}'
    device = ivtools.oei.OEI(ip)
    print(f'Configuring Offset in 40 ch DAPHNE {100+i} ')
    ivtools.Command(ip, f'CFG AFE ALL INITIAL')
    for ch in tqdm(range(40),unit='Channels'):
        ivtools.Command(ip, 'WR OFFSET CH ' + str(int(ch)) + ' V 1468', get_response=True)
        ivtools.Command(ip, 'CFG OFFSET CH ' + str(int(ch)) + ' GAIN 2', get_response=True)

    print(f'Configuring AFE registers 4, 51, 52 and Attenuators')
    for AFE in tqdm(range(5),unit='AFE'):
        ivtools.Command(ip, 'WR AFE '+ str(int(AFE)) + ' REG 52 V 21056', get_response=True)
        ivtools.Command(ip, 'WR AFE '+ str(int(AFE)) + ' REG 4 V 24', get_response=True)
        ivtools.Command(ip, 'WR AFE '+ str(int(AFE)) + ' REG 51 V 16', get_response=True)
        ivtools.Command(ip, 'WR AFE '+ str(int(AFE)) + ' VGAIN V 2667', get_response=True)
        alignment=[device.write_reg(0x2001,[1234]) for _ in range (3)]
    print('Finished writing commands.')





def main():
    p1  = multiprocessing.Process(target=configure, args=(4)
    p2  = multiprocessing.Process(target=configure, args=(5)
    p3  = multiprocessing.Process(target=configure, args=(7)
    p4  = multiprocessing.Process(target=configure, args=(9)
    #p11 = multiprocessing.Process(target=configure, args=(str(10.73.137.111))
    #p12 = multiprocessing.Process(target=configure, args=(str(10.73.137.112))
    #p13 = multiprocessing.Process(target=configure, args=(str(10.73.137.113))
    p1.start()
    p2.start()
    p3.start()
    p4.start()
    #p11.start()
    #p12.start()
    #p13.start()
if __name__ == "__main__":
    main()

