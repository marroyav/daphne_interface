import numpy as np
import matplotlib.pyplot as plt
import time
import os
import uproot
import click
from tqdm import tqdm
from ivtools import Daphne


@click.command()
@click.option("--steps", "-s", default=5, help="DAC counts per step")
@click.option("--ip_address", "-ip", default="7", help="Last numbers of the IP address (comma-separated)")
def main(steps, ip_address):
    """
    Simple IV scanner using both the BIAS and TRIM controls in DAPHNE.
    """
    # Channel and bias configurations
    map = {
        "7": {"apa": 1, "fbk": [0, 7, 8, 15], "hpk": [16, 23, 24, 31, 32, 39], "fbk_value": 806, "hpk_value": 1200},
        "4": {"apa": 1, "fbk": [0, 1, 2, 3, 4, 5, 6, 7], "hpk": [8, 9, 10, 11, 12, 13, 14, 15], "fbk_value": 1060, "hpk_value": 1560},
        "9": {"apa": 2, "fbk": list(range(16)), "hpk": list(range(16, 40)), "fbk_value": 1090, "hpk_value": 1585},
        "11": {"apa": 3, "fbk": list(range(24)), "hpk": list(range(24, 40)), "fbk_value": 1085, "hpk_value": 1590},
        "13": {"apa": 4, "fbk": [], "hpk": list(range(40)), "fbk_value": 0, "hpk_value": 1580},
    }

    # Process input IPs
    ips = ip_address.split(",")
    for ip in ips:
        if ip not in map:
            print(f"Invalid IP address suffix: {ip}. Allowed: {list(map.keys())}")
            return

        # Extract configuration for this endpoint
        config = map[ip]
        apa, fbk, hpk = config["apa"], config["fbk"], config["hpk"]
        fbk_value, hpk_value = config["fbk_value"], config["hpk_value"]
        full_ip = f"10.73.137.{int(ip) + 100}"

        # Initialize Daphne interface
        daphne = Daphne(full_ip)

        # Create output directory
        timestamp = time.strftime("%b-%d-%Y_%H%M", time.localtime())
        directory = f"../data/{timestamp}_IvCurves_trim_np04_apa{apa}_ip{ip}"
        os.makedirs(directory, exist_ok=True)

        # Disable bias initially
        daphne.command("WR VBIASCTRL V 0")

        # Iterate over channels and measure
        for ch in fbk + hpk:
            dac_bias, ecurrent = [], []
            bias_value = hpk_value if ch in hpk else fbk_value

            # Disable other channels on the same AFE
            other_channels = [x for x in fbk + hpk if x != ch and x // 8 == ch // 8]
            for other_ch in other_channels:
                daphne.command(f"WR TRIM CH {other_ch} V 4096")

            # Scan bias voltages
            for v in tqdm(range(bias_value - 270, bias_value, steps), desc=f"Channel {ch}..."):
                daphne.command(f"WR BIASSET AFE {ch // 8} V {v}")
                current = daphne.read_current(ch=ch)
                dac_bias.append(v)
                ecurrent.append(current)
                if current > 400:
                    break

            # Save data to ROOT file
            file_name = f"{directory}/apa_{apa}_afe_{ch//8}_ch_{ch}.root"
            with uproot.recreate(file_name) as f:
                f["tree/IV"] = {"bias": np.array(dac_bias), "current": np.array(ecurrent)}

            # Plot IV curve
            plt.figure()
            plt.plot(dac_bias, ecurrent, label=f"Channel {ch}: Bias {bias_value}")
            plt.title(f"IV Curve: APA {apa}, AFE {ch//8}, Channel {ch}")
            plt.xlabel("DAC Counts")
            plt.ylabel("Current (mA)")
            plt.gca().invert_xaxis()
            plt.legend()
            plt.grid()
            plt.savefig(f"{directory}/ivCurve_Channel_{ch}.png")
            plt.close()

        # Disable bias at the end
        daphne.command("WR VBIASCTRL V 0")
        daphne.close()


if __name__ == "__main__":
    main()