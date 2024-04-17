"""                                                               
Simple IV scanner using both the BIAS and TRIM controls in DAPHNE
double scan bias (forward) plus trim (backwards)
"""
import ivtools
import fnmatch, shutil,  click
from tqdm import tqdm
from time import localtime, strftime, sleep
from os import getcwd, chdir, mkdir
from uproot import recreate
from numpy import array


def ivscan(ip,bs,ts):

    map = {'10.73.137.104': {'apa': 1, 'fbk': [0, 1, 2, 3, 4, 5, 6, 7],
       'hpk': [8, 9, 10, 11, 12, 13, 14, 15],'fbk_value':1060,'hpk_value':1560},
   '10.73.137.105': {'apa': 1, 'fbk': [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 13, 15],
       'hpk': [17, 19, 20, 22],'fbk_value':1090,'hpk_value':1480},
   '10.73.137.107': {'apa': 1, 'fbk': [0, 2, 5, 7],
       'hpk': [8, 10, 13, 15],'fbk_value':1090,'hpk_value':1575},
   '10.73.137.109': {'apa': 2, 'fbk': [0, 1, 2, 3, 4, 5, 6, 7, 8, 10,  13, 15],
       'hpk': [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32,
           33, 34, 35, 36, 37, 38, 39],'fbk_value':1090,'hpk_value':1585},
   '10.73.137.111': {'apa': 3, 'fbk': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
       16, 17, 18, 19, 20, 21, 22, 23],
       'hpk': [24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39],
       'fbk_value':1085,'hpk_value':1590},
    '10.73.137.112': {'apa': 4, 'fbk': [],
       'hpk': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17, 18,
        19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 34, 37, 39],
       'fbk_value':0,'hpk_value':1580},
    '10.73.137.113': {'apa': 4, 'fbk': [0,2,5,7], 'hpk': [],'fbk_value':1040,'hpk_value':0},
}
    apa = map[ip]['apa']
    fbk = map[ip]['fbk']
    hpk = map[ip]['hpk']
    fbk_value = map[ip]['fbk_value']
    hpk_value = map[ip]['hpk_value']

    print(getcwd())
    print(localtime())
    t = localtime()
    timestamp = strftime('%b-%d-%Y_%H%M', t)
    BACKUP_NAME = ("backup-" + timestamp)
    directory = f'{timestamp}_IvCurves_trim_np04_apa{apa}_ip{ip}'
    chdir('../data/')
    mkdir(directory)
    chdir(directory)
    interface=ivtools.interface(ip)
    disable_bias=interface.command(f'WR VBIASCTRL V {0}')
    set_bias=[interface.command(f'WR BIASSET AFE {i} V {0}') for i in range (5)]
    apply_trim=[interface.command(f'WR TRIM CH {i} V {0}')for i in range (40)]
    enable_bias=interface.command(f'WR VBIASCTRL V {4000}')
    for ch in fbk + hpk:
        trim_dac=[]
        ecurrent=[]
        bias_dac=[]
        bias_measured=[]
        time_start = [strftime('%b-%d-%Y_%H%M', t)]
        bias_value = hpk_value if ch in hpk else fbk_value
        #set_bias=[interface.command(f'WR BIASSET AFE {ch//8} V {bias_value-400}')]
        #other_channels=list (filter(lambda x :x!=ch and ch//8 == x//8, fbk+hpk))
        for i in range(40):
            interface.command(f'WR TRIM CH {i} V {4096}')
        for bv in tqdm(range(bias_value-400, bias_value, bs), desc=f"Running bias scan on ch_{ch}..."):
            apply_bias_cmd = interface.command(f'WR BIASSET AFE {ch//8} V {bv}')
            k = interface.read_current(ch=ch,iterations=2)
            bias_dac.append(bv)
            bias_measured.append(interface.read_bias()[ch//8])
            if k > 100:
                for tv in tqdm(range(0, 2500, ts), desc=f"Running trim scan on ch_{ch}..."):
                    apply_trim_cmd = interface.command(f'WR TRIM CH {ch} V {tv}')
                    ecurrent.append(interface.read_current(ch=ch,iterations=3))
                    trim_dac.append(tv)
                name = f'apa_{apa}_afe_{ch//8}_ch_{ch}'
                time_end = [strftime('%b-%d-%Y_%H%M', t)]
                f = recreate(name + '.root')
                f["tree/bias"] = ({'bias_dac': array(bias_dac),'bias_v': array(bias_measured)})
                f["tree/iv_trim"] = ({'current': array(ecurrent),'trim': array(trim_dac)})
                f["tree/run"] = ({'time_start':array(time_start),'time_end': array(time_end)})

                channels_afe=list (filter(lambda x: ch//8 == x//8, fbk+hpk))
                for i in channels_afe:
                    interface.command(f'WR TRIM CH {i} V {0}')

                break

    disable_bias=interface.command( f'WR VBIASCTRL V {0}')
    set_bias=[interface.command( f'WR BIASSET AFE {i} V {0}') for i in range (5)]
    apply_trim=[interface.command( f'WR TRIM CH {i} V {0}') for i in range (40)]
    interface.close()


@click.command()
@click.option("--bias_steps", '-bs', default=5,help="DAC counts per step")
@click.option("--trim_steps", '-ts', default=20,help="DAC counts per step")
@click.option("--ip_address", '-ip', default='10.73.137.113',help="IP Address")

def main(ip_address,bias_steps,trim_steps):
    ivscan(ip_address,bias_steps,trim_steps)


if __name__ == "__main__":
    main()

