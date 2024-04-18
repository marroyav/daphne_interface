import argparse
import ivtools

def read_bias_on_ip(ip):
    daphne = ivtools.daphne('10.73.137.'+ip)
    print("Bias for endpoint",ip,daphne.read_bias())
    #k = daphne.read_bias()
    daphne.close()
    #print(k)

def main():
    parser = argparse.ArgumentParser(description="Read V for a given set of IPs")
    parser.add_argument('ips', nargs='*', help="List of IPs to apply commands (default: all IPs)")

    args = parser.parse_args()

    if not args.ips:
        print("No IP specified, reading V for all endponts")
        for ip in ['104','105','107','109','111','112','113']:
            read_bias_on_ip(ip)
    else:
        print("Reading V for endpoints",args.ips)
        for ip in args.ips:
            read_bias_on_ip(ip)

if __name__ == "__main__":
    main()