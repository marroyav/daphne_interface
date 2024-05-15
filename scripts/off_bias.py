import ivtools

def main():
    for j in [4,5,7,9,11,12,13]:
        daphne=ivtools.daphne(f'10.73.137.{100+j}')
        disable_bias=daphne.command(f'WR VBIASCTRL V {0}')
        set_bias=[daphne.command(f'WR BIASSET AFE {i} V {0}') for i in range (5)] 
        apply_trim=[daphne.command(f'WR TRIM CH {i} V {0}')for i in range (40)]
        print(daphne.read_bias())
if __name__ == "__main__":
    main()

