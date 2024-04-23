"""                                                               
Script to set operational BIAS and TRIM for each channel in DAPHNE
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
@click.option("--map_location", '-map', default="./../maps/",help="Input file with channel operation bias and trim mapping")
@click.option("--ip_address", '-ip', default="10.73.137.113",help="IP Address")
@click.option("--test", '-test', default=True,help="Whether the script prints the values or actually sets them")

def main(map_location,ip_address,test):

    map_file = map_location + ip_address + "_map.json"
    with open(map_file, "r") as fp: 
            map = json.load(fp)
        
    print("Imported map from ",map_file,":")
    print(map)

    apa = map['apa']
    fbk = map['fbk']
    hpk = map['hpk']
    fbk_op_bias = map['fbk_op_bias']
    hpk_op_bias = map['hpk_op_bias']
    fbk_op_trim = map['fbk_op_trim']
    hpk_op_trim = map['hpk_op_trim']
    
    #print(fbk,hpk,fbk_op_bias,hpk_op_bias,fbk_op_trim,hpk_op_trim)

    interface=ivtools.daphne(ip_address)
    disable_bias=interface.command(f'WR VBIASCTRL V {0}')
    set_bias=[interface.command(f'WR BIASSET AFE {i} V {0}') for i in range (5)]
    apply_trim=[interface.command(f'WR TRIM CH {i} V {0}')for i in range (40)]
    enable_bias=interface.command(f'WR VBIASCTRL V {4000}')

    for idx, ch in enumerate(fbk + hpk):

        if ch in fbk:
            if fbk_op_bias[ch//8] < 950:
                print("Setting bias in afe",ch//8, fbk_op_bias[ch//8])
                if not test: apply_bias_cmd = interface.command(f'WR BIASSET AFE {ch//8} V {fbk_op_bias[ch//8]}')
                print("Setting bias in ch",ch, fbk_op_trim[idx])
                if not test: apply_trim_cmd = interface.command(f'WR TRIM CH {ch} V {fbk_op_trim[idx]}')
            else:
                 print("Bias out of range - ABORT")
                 break

        elif ch in hpk:
            if hpk_op_bias[ch//8 - (len(fbk_op_bias))] < 1200:
                print("Setting bias in afe",ch//8, hpk_op_bias[ch//8 - (len(fbk_op_bias))])
                if not test: apply_bias_cmd = interface.command(f'WR BIASSET AFE {ch//8} V {hpk_op_bias[ch//8 - (len(fbk_op_bias))]}')
                print("Setting bias in ch",ch, hpk_op_trim[idx-len(fbk)])
                if not test: apply_trim_cmd = interface.command(f'WR TRIM CH {ch} V {hpk_op_trim[idx-len(fbk)]}')

    print("All set up, closing the interface")
    interface.close()


if __name__ == "__main__":
    main()
