"""
Simple IV scanner using both the BIAS and TRIM controls in DAPHNE
"""
import numpy as np
import ivtools
import matplotlib.pyplot as plt
import time, os, fnmatch, shutil, uproot, click
from tqdm import tqdm


@click.command()
# @click.argument("filename", type=click.Path(exists=True))
@click.option("--steps", '-s', default=5,help="DAC counts per step")
@click.option("--ip_address", '-ip', default='10.73.137.113',help="IP Address")
# @click.option("--quiet", '-q',help="Quiets debug outputs. Default: False.", is_flag=True)
# @click.option("--start-offset", '-s', default=0,help="Starting fragment offset. Default: 0")

def main(steps,ip_address):

    ip  = ip_address
    apa = 4
    fbk = [0,2,5,7]
    hpk = []
    fbk_value = 890
    hpk_value = 1360

    print(os.getcwd())
    print(time.localtime())
    t = time.localtime()
    timestamp = time.strftime('%b-%d-%Y_%H%M', t)
    BACKUP_NAME = ("backup-" + timestamp)
    directory = f'{timestamp}_IvCurves_trim_np04_apa{apa}_ip{ip}'
    os.mkdir(directory)
    os.chdir(directory)
    
    disable_bias=Command(ip, f'WR VBIASCTRL V {0}')
    set_bias=[Command(ip, f'WR BIASSET AFE {i} V {0}') for i in range (5)] 
    apply_trim=[Command(ip, f'WR TRIM CH {i} V {0}')for i in range (40)]
    enable_bias=Command(ip, f'WR VBIASCTRL V {4000}')
    for ch in fbk + hpk:
        breakd_v=[]
        dac_trim=[]
        dac_bias=[]
        evl_bias=[]
        ecurrent=[]
        bias_value = hpk_value if ch in hpk else fbk_value
        set_bias=[Command(ip, f'WR BIASSET AFE {ch//8} V {bias_value}')]
        init_timestamp = time.strftime('%b-%d-%Y_%H%M', time.localtime())
        for v in tqdm(range(0, 4095, steps), desc=f"Taking ch_{ch}..."):
            apply_trim_cmd = Command(ip, f'WR TRIM CH {ch} V {v}')
            k = ReadCurrent(ip, ch=ch)
            ecurrent.append(k.current)
            dac_trim.append(v)
        end_timestamp = time.strftime('%b-%d-%Y_%H%M', time.localtime())
        f=np.log(ecurrent, out=np.zeros_like(ecurrent), where=(ecurrent!=0))
        fpp=np.gradient(f)
        breakd_v=[dac_trim[np.argmin(fpp)]]
        name = f'apa_{apa}_afe_{ch//8}_ch_{ch}'
        f = uproot.recreate(name + '.root')
        f["tree/IV"] = ({'current': np.array(ecurrent),'trim': np.array(dac_trim)})
        f["tree/BDV"] = ({'breakdown_voltage': breakd_v,'init_ts':init_timestamp,'end_ts':end_timestamp})

        # Plotting code
        plt.figure()
        plt.plot(dac_trim, f, ',', linewidth=1, markersize=1, 
                 label=f'ch{ch}: BIAS {fbk_value if ch in fbk else hpk_value}, Trim {dac_trim[np.argmin(fpp)]}')
        plt.plot(dac_trim, fpp, ',', linewidth=1, markersize=1, color='r')
        plt.title(f'IV curve for APA {apa} AFE {ch//8} and ch {ch}')
        plt.xlabel('V DAC counts')
        plt.ylabel('Ln(I) U.A.')
        # plt.ylim([-0.5, 6])
        plt.gca().invert_xaxis()
        plt.legend(loc='upper left')
        # plt.show()
        plt.savefig(f'IVCurve_ch_{ch}.svg', bbox_extra_artists=(), bbox_inches='tight')

    disable_bias=Command(ip, f'WR VBIASCTRL V {0}')
    set_bias=[Command(ip, f'WR BIASSET AFE {i} V {0}') for i in range (5)] 
    apply_trim=[Command(ip, f'WR TRIM CH {i} V {0}')for i in range (40)]


                  
if __name__ == "__main__":
    main()
