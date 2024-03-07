import ivtools

def main():
    for i in [4,5,7,9,11,12,13]:
        ip=f'10.73.137.{100+i}'
        disable_bias=ivtools.Command(ip, f'WR VBIASCTRL V {0}')
        set_bias=[ivtools.Command(ip, f'WR BIASSET AFE {i} V {0}') for i in range (5)] 
        apply_trim=[ivtools.Command(ip, f'WR TRIM CH {i} V {0}')for i in range (40)]
        k = ivtools.ReadVoltages(ip)
        print(k.b_vector)
if __name__ == "__main__":
    main()

