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
@click.option("--bias_start", '-bb', default=400,help="starting bias DAC counts")
@click.option("--bias_step", '-bs', default=20,help="DAC counts per step")
@click.option("--trim_step", '-ts', default=40,help="trim DAC counts per step")
@click.option("--trim_max", '-tm', default=2500,help="maximum trim DAC counts")
@click.option("--current_thr", '-ct', default=1,help="maximum allowed current")
@click.option("--ip_address", '-ip', default="10.73.137.113",help="IP Address")

def main(map_file,bias_step,bias_start,trim_step,trim_max,current_thr,ip_address):
    
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
        current_trim_scan=[]
        bias_dac=[]
        bias_volt=[]
        current_bias_scan=[]
        
        time_start = [strftime('%b-%d-%Y_%H%M', time)]

        bias_vbd_hot = hpk_value if ch in hpk else fbk_value
        set_bias=[interface.command(f'WR BIASSET AFE {ch//8} V {bias_start}')]

        other_channels=list (filter(lambda x :x!=ch and ch//8 == x//8, fbk+hpk))

        for i in other_channels:

            interface.command(f'WR TRIM CH {i} V {4096}')

        for bv in tqdm(range(bias_start, bias_vbd_hot+bias_start, bias_step), desc=f"Running bias scan on ch_{ch}..."):

            apply_bias_cmd = interface.command(f'WR BIASSET AFE {ch//8} V {bv}')
            current = interface.read_current(ch=ch,iterations=2)

            bias_dac.append(bv)
            bias_volt.append(interface.read_bias()[ch//8])
            current_bias_scan.append(current)

            if current > current_thr:
                for tv in tqdm(range(0, trim_max, trim_step), desc=f"Running trim scan on ch_{ch}..."):

                    apply_trim_cmd = interface.command(f'WR TRIM CH {ch} V {tv}')
                    current_trim_scan.append(interface.read_current(ch=ch,iterations=4))
                    trim_dac.append(tv)

                time_end = [strftime('%b-%d-%Y_%H%M', time)]

                name = f'apa_{apa}_afe_{ch//8}_ch_{ch}'
                f = recreate(name + '.root')
                f["tree/bias"] = ({'bias_dac': array(bias_dac),'bias_v': array(bias_volt),'current':array(current_bias_scan)})
                f["tree/iv_trim"] = ({'trim': array(trim_dac),'current': array(current_trim_scan)})
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

