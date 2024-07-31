import ivtools
import click

@click.command()
@click.option("--ip_address", '-ip', default='10.73.137.113',help="IP Address")

def main(ip_address):
    ip=ip_address


    map={   '10.73.137.104':[821,1280,0,0,0],
        '10.73.137.105':[852,846,1303,0,0],
        '10.73.137.110':[850,1393,0,0,0],
        '10.73.137.109':[842,879,1274,1300,1265],
        '10.73.137.111':[847,853,822,1211,1297],
        '10.73.137.112':[1288,1296,1280,1313,1300],
        '10.73.137.113':[848,0,0,0,0]}


    disable_bias=ivtools.Command(ip, f'WR VBIASCTRL V {0}')
    set_bias=[ivtools.Command(ip, f'WR BIASSET AFE {i} V {0}') for i in range (5)]
    apply_trim=[ivtools.Command(ip, f'WR TRIM CH {i} V {0}')for i in range (40)]
    enable_bias=ivtools.Command(ip, f'WR VBIASCTRL V {4000}')

    for i in range (5):
        ivtools.Command(ip, f'WR BIASSET AFE {i} V {map[ip][i]}')

    read_bias=ivtools.ReadVoltages(ip)
    print(read_bias.b_vector)

if __name__ == "__main__":
    main()

