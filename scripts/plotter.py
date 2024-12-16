import ivtools
import numpy as np
import matplotlib.pyplot as plt
import time
# import json


# Configuration dictionary
config = {
    "daphne_ip_endpoint": 104,
    "channels": [0],
    "afes": [0, 1,2,3,4],
    "base_register": 0x40000000,   # Hexadecimal representation
    "afe_hex_base": 0x100000,     # Hexadecimal representation
    "channel_hex_base": 0x10000,  # Hexadecimal representation
    "colors": [
        "tab:blue", "tab:orange", "tab:green", "tab:red",
        "tab:purple", "tab:brown", "tab:gray", "tab:olive"
    ],
    "samples_per_channel": 20,
    "do_software_trigger": True,
    "software_trigger_value": 1234
}

def main():
    # config = load_config()

    # Load configuration variables
    daphne_ip_endpoint = config["daphne_ip_endpoint"]
    channels = config["channels"]
    AFEs = config["afes"]
    base_register = config["base_register"]
    AFE_hex_base = config["afe_hex_base"]
    channel_hex_base = config["channel_hex_base"]
    colors = config["colors"]
    samples_per_channel = config["samples_per_channel"]
    do_software_trigger = config["do_software_trigger"]
    software_trigger_value = config["software_trigger_value"]

    # Configure plotting layout dynamically
    if len(AFEs) == 1:
        figsize = (7, 5)
        nrows, ncols = 1, 1
    elif len(AFEs) == 2:
        figsize = (14, 5)
        nrows, ncols = 1, 2
    elif len(AFEs) == 3:
        figsize = (16.5, 4)
        nrows, ncols = 1, 3
    elif len(AFEs) >= 6:  # Special case for 6 AFEs
        figsize = (16, 9)
        nrows, ncols = 2, 3
    else:
        figsize = (16, 9)
        nrows, ncols = 2, 3

    plt.ion()  # Enable interactive plotting

    for t in [daphne_ip_endpoint]:
        daphne = ivtools.Daphne(f"10.73.137.{t}")
        total_time = 0
        fig, axes = plt.subplots(nrows=nrows, ncols=ncols, sharex=False, sharey=False, figsize=figsize)

        # Flatten axes for easy indexing
        axes = axes.flatten()

        # Special handling: remove the 6th plot if there are 6 AFEs
        if len(AFEs) == 6:
            fig.delaxes(axes[5])
            axes = np.delete(axes, 5)  # Remove from the list of axes

        if do_software_trigger:
            daphne.write_reg(0x2000, [software_trigger_value])  # Trigger SPI buffer

        for g, AFE in enumerate(AFEs):
            start = time.time()
            rec = [[] for _ in range(len(channels))]  # Store waveform data per channel

            for _ in range(samples_per_channel):  # Number of samples per channel
                for d, channel in enumerate(channels):
                    doutrec = daphne.read_fifo(base_register + (AFE_hex_base * AFE) + (channel_hex_base * channel), 50)
                    rec[d].extend(doutrec[2:])

            end = time.time()
            total_time += end - start

            ax = axes[g] if g < len(axes) else None
            if ax:
                ax.set_title(f"AFE{AFE}", fontsize=10)
                ax.set_xlabel("Samples", fontsize=8)
                ax.set_ylabel("14 bits data" if g % ncols == 0 else "")
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)

                for d, channel in enumerate(channels):
                    ax.plot(rec[d], linewidth=0.5, color=colors[channel], label=f'ch {channel}')
                ax.legend(loc="lower right", fontsize="xx-small", framealpha=0.5)

        plt.tight_layout()
        plt.show(block=False)
        print(f"Waveforms from IP Address 10.73.137.{t}")
        daphne.close()

     # Save the plot to a file
    plt.savefig(f"waveforms_endpoint_{daphne_ip_endpoint}.png", dpi=300, bbox_inches="tight")  # Save at high resolution
    plt.close()  # Close the figure to avoid memory issues
    print(f"Plot saved to waveforms_endpoint_{daphne_ip_endpoint}.png")


if __name__ == "__main__":
    main()