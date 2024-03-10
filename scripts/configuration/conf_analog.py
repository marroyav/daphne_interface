


import ivtools
from time import sleep
from tqdm import tqdm

def main():
    for i in [4,5,7,9,11,12,13]:
    #for i in [13]:
            ip=f'10.73.137.{100+i}'
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
            print('Finished writing commands.')

if __name__ == "__main__":
    main()

