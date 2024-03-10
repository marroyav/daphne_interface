import ivtools
import click

@click.command()
@click.option("--ip_address", '-ip', default='10.73.137.113',help="IP Address")

def main(ip_address):
    ip=ip_address


    map={   '10.73.137.104':[921,1380],
        '10.73.137.105':[952,946,1403],
        '10.73.137.107':[950,1393],
        '10.73.137.109':[942,979,1374,1400,1365],
        '10.73.137.111':[947,953,922,1411,1397],
        '10.73.137.112':[1388,1396,1380,1413,1400],
        '10.73.137.113':[948]}


    disable_bias=ivtools.Command(ip, f'WR VBIASCTRL V {0}')
    set_bias=[ivtools.Command(ip, f'WR BIASSET AFE {i} V {0}') for i in range (5)]
    apply_trim=[ivtools.Command(ip, f'WR TRIM CH {i} V {0}')for i in range (40)]
    enable_bias=ivtools.Command(ip, f'WR VBIASCTRL V {4000}')
    e=0
    for i in map[ip]:
        ivtools.Command(ip, f'WR BIASSET AFE {e} V {i-80}')
        e=e+1
    read_bias=ivtools.ReadVoltages(ip)
    print(read_bias.b_vector)

if __name__ == "__main__":
    main()

