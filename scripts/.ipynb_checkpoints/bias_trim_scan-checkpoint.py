"""                                                               
Simple IV scanner using both the BIAS and TRIM controls in DAPHNE
Modified version by Alessandro - double scan bias (forward) plus trim (backwards)
"""
import ivtools

#import matplotlib.pyplot as plt
import fnmatch, shutil,  click
from tqdm import tqdm
from time import localtime, strftime, sleep
from os import getcwd, chdir, mkdir
from uproot import recreate
from numpy import array
import json

@click.command()
@click.option("--map_file", '-map', default='iv_map.json',help="Input file with channel starting bias mapping")
@click.option("--bias_step", '-bs', default=10,help="DAC counts per step - bias")
@click.option("--trim_step", '-ts', default=40,help="DAC counts per step - trim")
@click.option("--ip_address", '-ip', default='10.73.137.113',help="IP Address")
def main(map_file,bias_step,trim_step,ip_address):
    
    ip=ip_address

    map = {
   '10.73.137.104': {'apa': 1, 'fbk': [0, 1, 2, 3, 4, 5, 6, 7],
       'hpk': [8, 9, 10, 11, 12, 13, 14, 15],'fbk_value':1060,'hpk_value':1560},
   '10.73.137.105': {'apa': 1, 'fbk': [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 13, 15],
       'hpk': [17, 19, 20, 22],'fbk_value':1090,'hpk_value':1480},
   '10.73.137.107': {'apa': 1, 'fbk': [0, 2, 5, 7],
       'hpk': [8, 10, 13, 15],'fbk_value':1090,'hpk_value':1575},
   '10.73.137.109': {'apa': 2, 'fbk': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
       'hpk': [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32,
           33, 34, 35, 36, 37, 38, 39],'fbk_value':1090,'hpk_value':1585},
   '10.73.137.111': {'apa': 3, 'fbk': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
       16, 17, 18, 19, 20, 21, 22, 23],
       'hpk': [24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39],
       'fbk_value':1085,'hpk_value':1590},
    '10.73.137.112': {'apa': 4, 'fbk': [],
       'hpk': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18,
        19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 34, 37, 39],
       'fbk_value':0,'hpk_value':1580},
    '10.73.137.113': {'apa': 4, 'fbk': [0,2,5,7], 'hpk': [],'fbk_value':1040,'hpk_value':0},
    #'10.73.137.113': {'apa': 4, 'fbk': [0], 'hpk': [],'fbk_value':1040,'hpk_value':0}
}

    with open(map_file, "r") as fp:
        map = json.load(fp)
    
    apa = map[ip_address]['apa']
    fbk = map[ip_address]['fbk']
    hpk = map[ip_address]['hpk']
    fbk_value = map[ip_address]['fbk_value']
    hpk_value = map[ip_address]['hpk_value']

    print(getcwd())
    print(localtime())
    t = localtime()
    timestamp = strftime('%b-%d-%Y_%H%M', t)
    BACKUP_NAME = ("backup-" + timestamp)
    directory = f'{timestamp}_IvCurves_trim_np04_apa{apa}_ip{ip}'
    chdir('../data/')
    mkdir(directory)
    chdir(directory)

    disable_bias=ivtools.Command(ip, f'WR VBIASCTRL V {0}')
    set_bias=[ivtools.Command(ip, f'WR BIASSET AFE {i} V {0}') for i in range (5)]
    apply_trim=[ivtools.Command(ip, f'WR TRIM CH {i} V {0}')for i in range (40)]
    enable_bias=ivtools.Command(ip, f'WR VBIASCTRL V {4000}')
    for ch in fbk + hpk:
        trim_dac=[]
        ecurrent=[]
        bias_dac=[]
        time_start = [strftime('%b-%d-%Y_%H%M', t)]
        bias_value = hpk_value if ch in hpk else fbk_value
        set_bias=[ivtools.Command(ip, f'WR BIASSET AFE {ch//8} V {bias_value-270}')]
        other_channels=list (filter(lambda x :x!=5 and ch//8 == x//8, fbk+hpk))
        for i in other_channels:
            ivtools.Command(ip, f'WR TRIM CH {i} V {4096}')
        for bv in tqdm(range(bias_value-270, bias_value, bias_step), desc=f"Running bias scan on ch_{ch}..."):
            apply_bias_cmd = ivtools.Command(ip, f'WR BIASSET AFE {ch//8} V {bv}')
            k = ivtools.ReadCurrent(ip, ch=ch)
            measurement=k.current
            if measurement > 100:
                bias_dac.append(bv)
                for tv in tqdm(range(0, 2500, trim_step), desc=f"Running trim scan on ch_{ch}..."):
                    apply_trim_cmd = ivtools.Command(ip, f'WR TRIM CH {ch} V {tv}')
                    k = ivtools.ReadCurrent(ip, ch=ch)
                    measurement=k.current
                    ecurrent.append(measurement)
                    trim_dac.append(tv)
                name = f'apa_{apa}_afe_{ch//8}_ch_{ch}'
                time_end = [strftime('%b-%d-%Y_%H%M', t)]
                f = recreate(name + '.root')
                f["tree/IV"] = ({'current': array(ecurrent),'trim': array(trim_dac)})
                f["tree/run"] = ({'bias': array(bias_dac),'time_start': array(time_start),'time_end': array(time_end)})
                break
        ## Plotting code 
        #plt.figure()
        #plt.plot(trim_dac, ecurrent, ',', linewidth=1, markersize=1,
        #        label=f'ch{ch}: BIAS {fbk_value if ch in fbk else hpk_value}')
        ##plt.plot(trim_dac, fpp, ',', linewidth=1, markersize=1, color='r')
        #plt.title(f'IV curve for APA {apa} AFE {ch//8} and ch {ch}')                                                                                                   #                                                    
        #plt.xlabel('V DAC counts')                           
        #plt.ylabel('Ln(I) U.A.')
        #plt.ylim([-0.5, 6])
        #plt.gca().invert_xaxis()
        #plt.legend(loc='upper left')                          
        ##plt.show() 
        #plt.savefig(f'ivCurvesEndpoint{ch}.png', bbox_extra_artists=(), bbox_inches='tight')                                                                   


    disable_bias=ivtools.Command(ip, f'WR VBIASCTRL V {0}')
    set_bias=[ivtools.Command(ip, f'WR BIASSET AFE {i} V {0}') for i in range (5)]
    apply_trim=[ivtools.Command(ip, f'WR TRIM CH {i} V {0}')for i in range (40)]



if __name__ == "__main__":
    main()
