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
@click.option("--map_file", '-map', default="./../maps/iv_map.json",help="Input file with channel starting bias mapping")
@click.option("--bias_start_hpk", '-bsh', default=850,help="Starting bias DAC counts for HPK")
@click.option("--bias_start_fbk", '-bsf', default=500,help="Starting bias DAC counts for FBK")
@click.option("--bias_step", '-bs', default=10,help="DAC counts per step")
@click.option("--trim_step", '-ts', default=20,help="Trim DAC counts per step")
@click.option("--trim_max", '-tm', default=3800,help="Maximum trim DAC counts")
@click.option("--current_thr_hpk", '-cth', default=0.6,help="Maximum allowed current for HPK")
@click.option("--current_thr_fbk", '-ctf', default=0.4,help="Maximum allowed current for FBK")
@click.option("--point_iterations", '-it', default=4,help="Number of iterations per point")
@click.option("--ip_address", '-ip', default="10.73.137.113",help="IP Address")

def main(map_file,bias_start_hpk,bias_start_fbk,bias_step,trim_step,trim_max,current_thr_hpk,current_thr_fbk,point_iterations,ip_address):
    
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
    print("Setting maximum bias value of", fbk_value, "for FBK chhannels", fbk)
    print("Setting maximum bias value of", hpk_value, "for HPK chhannels", hpk)

    time = localtime()
    print("Run started at ",time)
    timestamp = strftime('%b-%d-%Y_%H%M', time)

    print("Working in directory ",getcwd())
    directory = f'{timestamp}_IvCurves_trim_np04_apa{apa}_ip{ip_address}'
    chdir('../data/')
    mkdir(directory)
    chdir(directory)

    interface=ivtools.daphne(ip_address)
    disable_bias=interface.command(f'WR VBIASCTRL V {0}')
    set_bias=[interface.command(f'WR BIASSET AFE {i} V {0}') for i in range (5)]
    apply_trim=[interface.command(f'WR TRIM CH {i} V {0}')for i in range (40)]
    enable_bias=interface.command(f'WR VBIASCTRL V {4000}')

    for idx, ch in enumerate(fbk + hpk):

        trim_dac=[]
        current_trim_scan=[]
        bias_dac=[]
        bias_volt=[]
        current_bias_scan=[]
        
        time_start = [strftime('%b-%d-%Y_%H%M', localtime())]

        bias_stop = hpk_value[idx-len(fbk)] if ch in hpk else fbk_value[idx]
        set_bias=[interface.command(f'WR BIASSET AFE {ch//8} V {bias_start_hpk if ch in hpk else bias_start_fbk}')]

        other_channels=list (filter(lambda x :x!=ch and ch//8 == x//8, fbk+hpk))

        for i in other_channels:

            interface.command(f'WR TRIM CH {i} V {4096}')

        for bv in tqdm(range(bias_start_hpk if ch in hpk else bias_start_fbk, bias_stop, bias_step), desc=f"Running bias scan on ch_{ch}..."):

            apply_bias_cmd = interface.command(f'WR BIASSET AFE {ch//8} V {bv}')
            current = interface.read_current(ch=ch,iterations=point_iterations)

            bias_dac.append(bv)
            bias_volt.append(interface.read_bias()[ch//8])
            current_bias_scan.append(current)

            if (abs(current) > abs(current_thr_hpk) and ch in hpk) or (abs(current) > abs(current_thr_fbk) and ch in fbk) or bv >= bias_stop-bias_step:
                
                for tv in tqdm(range(0, trim_max, trim_step), desc=f"Running trim scan on ch_{ch}..."):

                    apply_trim_cmd = interface.command(f'WR TRIM CH {ch} V {tv}')
                    current_trim_scan.append(interface.read_current(ch=ch,iterations=4))
                    trim_dac.append(tv)

                time_end = [strftime('%b-%d-%Y_%H%M', localtime())]

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

