import argparse
import ivtools

def reset_bias_trim(ip):
    daphne = ivtools.interface(ip)
    disable_bias = daphne.command('WR VBIASCTRL V 0')
    reset_bias = [daphne.command(f'WR BIASSET AFE {i} V 0') for i in range(5)]
    reset_trim = [daphne.command(f'WR TRIM CH {i} V 0') for i in range(40)]
    print("Bias for endpoint",ip,daphne.read_bias())

def main():
    parser = argparse.ArgumentParser(description="Set bias and trim to 0 for a given set of IPs")
    parser.add_argument('ips', nargs='*', help="List of IPs to apply commands (default: all IPs)")

    args = parser.parse_args()

    if not args.ips:
        print("No IP specified, resetting bias and trim for all endponts")
        for j in [4, 5, 7, 9, 11, 12, 13]:
            ip = f'10.73.137.{100 + j}'
            reset_bias_trim(ip)
    else:
        print("Resetting bias and trim for endpoints",args.ips)
        for ip in args.ips:
            reset_bias_trim(ip)

if __name__ == "__main__":
    main()
