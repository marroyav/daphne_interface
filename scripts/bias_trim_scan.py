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
import json

@click.command()
@click.option("--map_file", '-map', default="iv_map.json",help="Input file with channel starting bias mapping")
@click.option("--bias_step", '-bs', default=5,help="DAC counts per step")
@click.option("--trim_step", '-ts', default=20,help="DAC counts per step")
@click.option("--ip_address", '-ip', default="10.73.137.113",help="IP Address")

def main(map_file,bias_step,trim_step,ip_address):

    with open(map_file, "r") as fp:
        map = json.load(fp)
        
    print("Imported map from ",map_file,":")
    print(map)

    apa = map[ip_address]['apa']
    fbk = map[ip_address]['fbk']
    hpk = map[ip_address]['hpk']
    fbk_value = map[ip_address]['fbk_value']
    hpk_value = map[ip_address]['hpk_value']
    
    print("Scanning APA", apa)
    print("Setting starting bias value of", fbk_value, "for FBK chhannels", fbk)
    print("Setting starting bias value of", hpk_value, "for HPK chhannels", hpk)

    time = localtime()
    print("Run started at ",time)
    timestamp = strftime('%b-%d-%Y_%H%M', time)

    print("Working in directory ",getcwd())
    directory = f'{timestamp}_IvCurves_trim_np04_apa{apa}_ip{ip_address}'
    chdir('../data/')
    mkdir(directory)
    chdir(directory)

    interface=ivtools.interface(ip_address)
    disable_bias=interface.command(f'WR VBIASCTRL V {0}')
    set_bias=[interface.command(f'WR BIASSET AFE {i} V {0}') for i in range (5)]
    apply_trim=[interface.command(f'WR TRIM CH {i} V {0}')for i in range (40)]
    enable_bias=interface.command(f'WR VBIASCTRL V {4000}')

    for ch in fbk + hpk:

        trim_dac=[]
        ecurrent=[]
        bias_dac=[]
        bias_measured=[]
        
        time_start = [strftime('%b-%d-%Y_%H%M', time)]

        bias_value = hpk_value if ch in hpk else fbk_value
        set_bias=[interface.command(f'WR BIASSET AFE {ch//8} V {bias_value-400}')]

        other_channels=list (filter(lambda x :x!=ch and ch//8 == x//8, fbk+hpk))

        for i in other_channels:

            interface.command(f'WR TRIM CH {i} V {4096}')

        for bv in tqdm(range(bias_value-400, bias_value, bias_step), desc=f"Running bias scan on ch_{ch}..."):

            apply_bias_cmd = interface.command(f'WR BIASSET AFE {ch//8} V {bv}')
            k = interface.read_current(ch=ch,iterations=2)
            bias_dac.append(bv)
            bias_measured.append(interface.read_bias()[ch//8])

            if k > 100:
                for tv in tqdm(range(0, 2500, trim_step), desc=f"Running trim scan on ch_{ch}..."):

                    apply_trim_cmd = interface.command(f'WR TRIM CH {ch} V {tv}')
                    ecurrent.append(interface.read_current(ch=ch,iterations=3))
                    trim_dac.append(tv)

                time_end = [strftime('%b-%d-%Y_%H%M', time)]

                name = f'apa_{apa}_afe_{ch//8}_ch_{ch}'
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

if __name__ == "__main__":
    main()

