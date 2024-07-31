import ivtools, click

@click.command()
@click.option("--ip_address", '-ip', default='ALL',help="IP Address")
@click.option("--mode", '-m', default='OP',help="Bias Mode")

def main(mode,ip_address):
    # Breakdown values
    v_bd = {   
            '10.73.137.104':[675,1000],
            '10.73.137.105':[690,680,1080],
            '10.73.137.110':[690,1020],
            '10.73.137.109':[680,710,1100,1070,1030],
            '10.73.137.111':[690,700,680,1080,1080],
            '10.73.137.112':[1080,1000,1060,1060,1080],
            '10.73.137.113':[690]
          }
    # Breakdown values (v<1000)+115 (v>1000)+78
    v_op = {   
            '10.73.137.104':[790,1078],
            '10.73.137.105':[805,795,1158],
            '10.73.137.110':[805,1098],
            '10.73.137.109':[795,825,1178,1148,1108],
            '10.73.137.111':[805,815,795,1158,1158],
            '10.73.137.112':[1158,1078,1138,1138,1158],
            '10.73.137.113':[805]
          }
    
    v_op = {   
            '10.73.137.104':[790,1078],
            '10.73.137.105':[805,795,1158],
            '10.73.137.110':[805,1098],
            '10.73.137.109':[795,825,1178,1148,1108],
            '10.73.137.111':[805,815,795,1158,1158],
            '10.73.137.112':[0,1158,0,0,0],
            '10.73.137.113':[805]
          }
    v_noise_test = {
            '10.73.137.104':[650,970],
            '10.73.137.105':[660,650,1050],
            '10.73.137.110':[660,990],
            '10.73.137.109':[650,680,1070,1040,1000],
            '10.73.137.111':[660,670,650,1050,1050],
            '10.73.137.112':[1050,970,1030,1030,1050],
            '10.73.137.113':[660]
    }
    
    if ip_address=="ALL": your_ips = [4,5,10,9,11,12,13]; print("No IP specified, reading all endpoints")
    else: your_ips = list(map(int, list(ip_address.split(","))))

    for ip in your_ips:
        if ip not in [4,5,10,9,11,12,13]: 
            print("\033[91mInvalid IP address, please choose your ip between 4,5,10,9,11,12,13 :)\033[0m"); 
            exit()
        ip=f"10.73.137.{100+ip}"
        interface = ivtools.daphne(ip)
        trim = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]

        disable_bias = interface.command( f'WR VBIASCTRL V {0}')
        set_bias = [interface.command( f'WR BIASSET AFE {i} V {0}') for i in range (1)]
        apply_trim = [interface.command( f'WR TRIM CH {i} V {trim[i]}')for i in range(len(trim))]
        enable_bias = interface.command( f'WR VBIASCTRL V {4095}')
        if   mode == 'OP':    v_used = v_op
        elif mode == 'BD':    v_used = v_bd
        elif mode == 'NOISE': v_used = v_noise_test
        else: print("ERROR: no Valid operation mode"); break

        for vdx,v_value in enumerate(v_used[ip]):
            interface.command( f'WR BIASSET AFE {vdx} V {v_value}')
        print("Bias for endpoint",ip,interface.read_bias())


if __name__ == "__main__":
    main()