import ivtools
import click

@click.command()
@click.option("--ip_address", '-ip', default='10.73.137.113',help="IP Address")

def main(ip_address):
    daphne=ivtools.interface(ip_address)


    map={   '10.73.137.104':[921,1380],
        '10.73.137.105':[952,946,1403],
        '10.73.137.107':[950,1393],
        '10.73.137.109':[942,979,1374,1400,1365],
        '10.73.137.111':[947,953,922,1411,1397],
        '10.73.137.112':[1388,1396,1380,1413,1400],
        '10.73.137.113':[960]}
    trim=[900,0,1340,0,0,840,0,1110]

    disable_bias=daphne.command( f'WR VBIASCTRL V {0}')
    set_bias=[daphne.command( f'WR BIASSET AFE {i} V {0}') for i in range (1)]
    apply_trim=[daphne.command( f'WR TRIM CH {i} V {trim[i]}')for i in range(len(trim))]
    enable_bias=daphne.command( f'WR VBIASCTRL V {4095}')
    e=0
    for i in map[ip_address]:
        daphne.command( f'WR BIASSET AFE {e} V {i}')
        e=e+1
    print(daphne.read_bias())

if __name__ == "__main__":
    main()

