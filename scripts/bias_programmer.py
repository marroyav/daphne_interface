import ivtools, click

@click.command()
@click.option("--ip_address", '-ip', default='10.73.137.113',help="IP Address")
def main(ip_address):
    interface = ivtools.daphne(ip_address)
    # trim = [900,0,1340,0,0,840,0,1110]
    
    # Breakdown values
    v_bd = {   
            '10.73.137.104':[675,1000],
            '10.73.137.105':[690,680,1080],
            '10.73.137.107':[690,1020],
            '10.73.137.109':[680,710,1100,1070,1030],
            '10.73.137.111':[690,700,680,1080,1080],
            '10.73.137.112':[1080,1000,1060,1060,1080],
            '10.73.137.113':[690]
          }
    # Breakdown values (v<1000)+115 (v>1000)+78
    v_op = {   
            '10.73.137.104':[790,1078],
            '10.73.137.105':[805,795,1158],
            '10.73.137.107':[805,1098],
            '10.73.137.109':[795,825,1178,1148,1108],
            '10.73.137.111':[805,815,795,1158,1158],
            '10.73.137.112':[1158,1078,1138,1138,1158],
            '10.73.137.113':[805]
          }

    disable_bias = interface.command( f'WR VBIASCTRL V {0}')
    set_bias = [interface.command( f'WR BIASSET AFE {i} V {0}') for i in range (1)]
    # apply_trim = [interface.command( f'WR TRIM CH {i} V {trim[i]}')for i in range(len(trim))]
    enable_bias = interface.command( f'WR VBIASCTRL V {4095}')
    for vdx,v_value in enumerate(v_op[ip_address]):
        interface.command( f'WR BIASSET AFE {vdx} V {v_value}')
    print(interface.read_bias())


if __name__ == "__main__":
    main()