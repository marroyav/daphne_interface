import argparse
import ivtools

def read_bias_on_ip(ip):
    daphne = ivtools.interface('10.73.137.' + str(100 + int(ip)))
    k = daphne.read_bias()
    print(k)

def main():
    parser = argparse.ArgumentParser(description="Read V for a given set of IPs")
    parser.add_argument('ips', nargs='*', help="List of IPs to apply commands (default: all IPs)")

    args = parser.parse_args()

    if not args.ips:
        print("No IP specified, reading V for all endponts")
        for ip in [4, 5, 7, 9, 11, 12, 13]:
            read_bias_on_ip(ip)
    else:
        print("Reading V for endpoint",args.ips)
        for ip in args.ips:
            read_bias_on_ip(ip)

if __name__ == "__main__":
    main()