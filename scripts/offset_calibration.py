import numpy as np
import matplotlib.pyplot as plt
import time
import logging
from ivtools import Daphne
import re

# --- CONFIGURATION ---
TARGET_BASELINE = 4000
TARGET_BAND = 2  # ±10 ADC counts tolerance band
NUM_WAVEFORMS = 3
SAMPLES = 4000
MAX_ITERATIONS = 7
IP = "10.73.137.107"
CHANNELS_TO_ACQUIRE = {
    0: [0, 7],
    1: [0, 7],
    2: [0, 7],
    3: [0, 7],
    4: list(range(8))
    # 4: [1]
}
OFFSET_MIN = 2000
OFFSET_MAX = 2500
DEFAULT_VALUE = 2250

# Flattened list of global channels
CHANNELS = [afe * 8 + ch for afe, local_chs in CHANNELS_TO_ACQUIRE.items() for ch in local_chs]

# Setup logging
logging.basicConfig(
    filename="offset_tuning.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s | %(message)s")
console.setFormatter(formatter)
logging.getLogger().addHandler(console)

# AFE mapping: ch_global -> (afe, ch_local)
def get_afe_and_local_channel(ch_global):
    return ch_global // 8, ch_global % 8

# Initialize hardware interface
daphne = Daphne(IP)

def read_offsets():
    """Read current offset values from hardware"""
    channels_data = []
    for ch in CHANNELS:
        try:
            response = daphne.command(f'RD OFFSET CH {ch}')
            match = re.search(r'OFFSET DAC REG= (\d+).*DAC GAIN=(\d+)', response)
            if match:
                dac_reg, dac_gain = map(int, match.groups())
                channels_data.append({'Channel': ch, 'DAC_REG': dac_reg, 'DAC_GAIN': dac_gain})
            else:
                channels_data.append({'Channel': ch, 'DAC_REG': DEFAULT_VALUE, 'DAC_GAIN': 0})
        except Exception as e:
            channels_data.append({'Channel': ch, 'DAC_REG': DEFAULT_VALUE, 'DAC_GAIN': 0})
    return {item['Channel']: item for item in channels_data}

def acquire_waveforms():
    """Acquire and process waveform data"""
    results = {}
    for ch in CHANNELS:
        afe, ch_local = get_afe_and_local_channel(ch)
        waveforms = []
        for _ in range(NUM_WAVEFORMS):
            wf = daphne.read_waveform(afe, ch_local, samples=SAMPLES)
            if wf.size > 0:
                waveforms.append(wf)
        if waveforms:
            stacked = np.stack(waveforms)
            mean = np.mean(stacked[:, :4000])
            std = np.std(stacked[:, :4000])
            results[ch] = (mean, std)
    return results

def adjust_offsets(results):
    """Adjust offsets with decreasing step size and target band locking"""
    for ch, (mean, std) in results.items():
        if locked[ch]:
            continue
            
        afe, _ = get_afe_and_local_channel(ch)
        current_offset = channel_offsets[ch]['DAC_REG']
        error = TARGET_BASELINE - mean
        
        # Handle inversion for channels >= 32
        if ch >= 32:
            error *= -1

        # Check if within target band
        if abs(error) <= TARGET_BAND:
            locked[ch] = True
            logging.info(f"CH{ch:02} locked in target band | mean={mean:.1f}")
            continue

        if ch not in step_sizes:
            step_sizes[ch] = 10  # Initial large step
            
        # Reduce step size if oscillating
        if len(history[ch]) > 2:
            last_means = [h[0] for h in history[ch][-3:]]
            if (last_means[-1] - last_means[-2]) * (last_means[-2] - last_means[-3]) < 0:
                step_sizes[ch] = max(1, step_sizes[ch] // 2)
        
        delta = np.sign(error) * step_sizes[ch]
        new_offset = int(np.clip(current_offset + delta, OFFSET_MIN, OFFSET_MAX))
        
        # Apply changes
        daphne.command(f'WR OFFSET CH {ch} V {new_offset}')
        channel_offsets[ch]['DAC_REG'] = new_offset
        
        # Reduce step size for next iteration
        if step_sizes[ch] > 1:
            step_sizes[ch] = max(1, step_sizes[ch] // 2)
        
        logging.info(f"CH{ch:02} (AFE{afe}): {current_offset} → {new_offset} | Δ={delta}, mean={mean:.1f}")

        history[ch].append((mean, std))

# --- MAIN PROGRAM ---
if __name__ == "__main__":
    # Initialize data structures
    channel_offsets = read_offsets()
    history = {ch: [] for ch in CHANNELS}
    locked = {ch: False for ch in CHANNELS}
    step_sizes = {}

    print("Initial offsets:")
    for ch in sorted(channel_offsets.keys()):
        print(f"CH{ch:02}: {channel_offsets[ch]['DAC_REG']}")

    # Main calibration loop
    for iteration in range(MAX_ITERATIONS):
        logging.info(f"--- Iteration {iteration + 1} ---")
        results = acquire_waveforms()
        
        if all(locked[ch] for ch in CHANNELS):
            logging.info("🎯 All channels within target band.")
            break

        adjust_offsets(results)
        time.sleep(1)

    # Final reporting
    logging.info("✅ Calibration complete.")
    logging.info("Final offsets per channel:")
    for ch in sorted(channel_offsets.keys()):
        logging.info(f"CH{ch:02}: {channel_offsets[ch]['DAC_REG']}")

    # Plot results with target band
    plt.figure(figsize=(12, 6))
    for ch in CHANNELS:
        means = [entry[0] for entry in history[ch]]
        plt.plot(means, label=f"CH{ch:02}", alpha=0.6)

    plt.axhline(TARGET_BASELINE, linestyle='--', color='black', label='Target')
    plt.fill_between(
        range(len(next(iter(history.values())))),
        TARGET_BASELINE - TARGET_BAND,
        TARGET_BASELINE + TARGET_BAND,
        alpha=0.2,
        color='green',
        label="Target Band"
    )
    plt.xlabel("Iteration")
    plt.ylabel("Baseline Mean (ADC counts)")
    plt.title(f"Offset Tuning Convergence (±{TARGET_BAND} ADC band)")
    plt.grid(True)
    plt.tight_layout()
    plt.legend(ncol=2, bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Save the plot before showing it
    plot_filename = f"offset_tuning_{time.strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
    logging.info(f"Saved convergence plot as {plot_filename}")
    
    plt.show()


    print("\nFinal offsets:")
    print([channel_offsets[ch]['DAC_REG'] for ch in sorted(CHANNELS)])