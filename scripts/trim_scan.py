"""
Simple IV scanner using both the BIAS and TRIM controls in DAPHNE
"""
import numpy as np
import ivtools
import matplotlib.pyplot as plt
import time, os, fnmatch, shutil, uproot, click
from tqdm import tqdm

@click.command()
@click.option("--steps", '-s', default=5,help="DAC counts per step")
@click.option("--ip_address", '-ip', default='10.73.137.113',help="IP Address")

def main(steps,ip_address):
    ip=ip_address

    map = {
   '10.73.137.104': {'apa': 1, 'fbk': [0, 1, 2, 3, 4, 5, 6, 7],
       'hpk': [8, 9, 10, 11, 12, 13, 14, 15],'fbk_value':860,'hpk_value':1360},
   '10.73.137.105': {'apa': 1, 'fbk': [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 13, 15],
       'hpk': [17, 19, 20, 22],'fbk_value':890,'hpk_value':1380},
   '10.73.137.110': {'apa': 1, 'fbk': [0, 2, 5, 7],
       'hpk': [8, 10, 13, 15],'fbk_value':890,'hpk_value':1375},
   '10.73.137.109': {'apa': 2, 'fbk': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
       'hpk': [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32,
           33, 34, 35, 36, 37, 38, 39],'fbk_value':890,'hpk_value':1385},
   '10.73.137.111': {'apa': 3, 'fbk': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
       16, 17, 18, 19, 20, 21, 22, 23],
       'hpk': [24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39],
       'fbk_value':885,'hpk_value':1390},
   '10.73.137.112': {'apa': 4, 'fbk': [],
       'hpk': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18,
           19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 34, 37, 39],
       'fbk_value':0,'hpk_value':1380},
   '10.73.137.113': {'apa': 4, 'fbk': [0,2,5,7], 'hpk': [],'fbk_value':890,'hpk_value':0},
}

    apa = map[ip_address]['apa']
    fbk = map[ip_address]['fbk']
    hpk = map[ip_address]['hpk']
    fbk_value = map[ip_address]['fbk_value']
    hpk_value = map[ip_address]['hpk_value']

    print(os.getcwd())
    print(time.localtime())
    t = time.localtime()
    timestamp = time.strftime('%b-%d-%Y_%H%M', t)
    BACKUP_NAME = ("backup-" + timestamp)
    directory = f'{timestamp}_IvCurves_trim_np04_apa{apa}_ip{ip}'
    os.chdir('../data/')
    os.mkdir(directory)
    os.chdir(directory)
    
    disable_bias=ivtools.Command(ip, f'WR VBIASCTRL V {0}')
    set_bias=[ivtools.Command(ip, f'WR BIASSET AFE {i} V {0}') for i in range (5)] 
    apply_trim=[ivtools.Command(ip, f'WR TRIM CH {i} V {0}')for i in range (40)]
    enable_bias=ivtools.Command(ip, f'WR VBIASCTRL V {4000}')
    for ch in fbk + hpk:
        breakd_v=[]
        dac_trim=[]
        dac_bias=[]
        evl_bias=[]
        ecurrent=[]
        bias_value = hpk_value if ch in hpk else fbk_value
        set_bias=[ivtools.Command(ip, f'WR BIASSET AFE {ch//8} V {bias_value}')]
        #init_timestamp = time.strftime('%b-%d-%Y_%H%M', time.localtime())
        for v in tqdm(range(0, 4095, steps), desc=f"Taking ch_{ch}..."):
            apply_trim_cmd = ivtools.Command(ip, f'WR TRIM CH {ch} V {v}')
            k = ivtools.ReadCurrent(ip, ch=ch)
            ecurrent.append(k.current)
            dac_trim.append(v)
        #end_timestamp = time.strftime('%b-%d-%Y_%H%M', time.localtime())
        x=np.add(ecurrent,np.average(ecurrent[-50:]))
        f=np.add(np.log(x),0)
        fpp=np.multiply((np.multiply(np.gradient(f),1/f)),-1)
        #fpp=np.gradient(ecurrent)
        breakd_v=[dac_trim[np.argmax(fpp)]]
        name = f'apa_{apa}_afe_{ch//8}_ch_{ch}'
        f = uproot.recreate(name + '.root')
        f["tree/IV"] = ({'current': np.array(ecurrent),'trim': np.array(dac_trim)})
        f["tree/BDV"] = ({'breakdown_voltage': breakd_v
        #   ,'init_ts':init_timestamp,'end_ts':end_timestamp
            })

        # Plotting code
        plt.figure()
        plt.plot(dac_trim, ecurrent, ',', linewidth=1, markersize=1, 
                 label=f'ch{ch}: BIAS {fbk_value if ch in fbk else hpk_value}, Trim {dac_trim[np.argmax(fpp)]}')
        plt.plot(dac_trim, fpp, ',', linewidth=1, markersize=1, color='r')
        plt.title(f'IV curve for APA {apa} AFE {ch//8} and ch {ch}')
        plt.xlabel('V DAC counts')
        plt.ylabel('Ln(I) U.A.')
        plt.yscale('log')
        # plt.ylim([-0.5, 6])
        plt.gca().invert_xaxis()
        plt.legend(loc='upper left')
        # plt.show()
        plt.savefig(f'IVCurve_ch_{ch}.svg', bbox_extra_artists=(), bbox_inches='tight')

    disable_bias=ivtools.Command(ip, f'WR VBIASCTRL V {0}')
    set_bias=[ivtools.Command(ip, f'WR BIASSET AFE {i} V {0}') for i in range (5)] 
    apply_trim=[ivtools.Command(ip, f'WR TRIM CH {i} V {0}')for i in range (40)]


                  
if __name__ == "__main__":
    main()
