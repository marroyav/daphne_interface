import numpy as np
import matplotlib.pyplot as plt
from time import sleep
from ivtools import Daphne  

class ReadWaveforms:
    def __init__(self, ip, afe=0, ch=0, samples=1000, plot=False):
        """
        Reads waveforms from a specific AFE and channel on a given device.
        """
        self.ip = ip
        self.afe = afe
        self.ch = ch
        self.samples = samples
        self.plot = plot
        self.waveform = self._read_waveform()

        if self.plot:
            self._plot_waveform()

    def _read_waveform(self):
        """
        Reads waveform data from the specified channel.
        """
        with Daphne(self.ip) as device:
            # Trigger spy buffers
            device.write_reg(0x2000, [1234])

            # Read waveform data in chunks of 50 samples
            waveform = []
            for i in range(self.samples // 50):
                data = device.read_reg(
                    0x40000000 + (0x100000 * self.afe) + (0x10000 * self.ch) + (i * 50),
                    size=50
                )
                waveform.extend(data[2:])  # Skip header bytes

        return np.array(waveform)

    def _plot_waveform(self):
        """
        Plots the waveform data.
        """
        time_axis = np.arange(0, len(self.waveform)) * 16e-9  # Time axis in seconds
        plt.figure(figsize=(10, 5))
        plt.plot(time_axis, self.waveform, linewidth=0.6)
        plt.xlabel("Time (s)")
        plt.ylabel("Amplitude")
        plt.title(f"Waveform for AFE {self.afe}, Channel {self.ch}")
        plt.grid()
        plt.show()

class FFTAnalysis:
    def __init__(self, signal, sampling_rate=1/16e-9, plot=False):
        """
        Computes and optionally plots the FFT of a signal.
        """
        self.signal = signal
        self.sampling_rate = sampling_rate
        self.freqs, self.fft_magnitude = self._compute_fft()

        if plot:
            self._plot_fft()

    def _compute_fft(self):
        """
        Computes the FFT of the signal.
        """
        n = len(self.signal)
        fft_values = np.fft.fft(self.signal) / n  # Normalize FFT
        fft_freqs = np.fft.fftfreq(n, d=1/self.sampling_rate)  # Frequency axis
        pos_indices = np.where(fft_freqs >= 0)  # Keep positive frequencies only
        return fft_freqs[pos_indices], 20 * np.log10(np.abs(fft_values[pos_indices]))

    def _plot_fft(self):
        """
        Plots the FFT of the signal.
        """
        plt.figure(figsize=(10, 5))
        plt.plot(self.freqs / 1e6, self.fft_magnitude)  # Convert to MHz
        plt.xscale("log")
        plt.ylim([-140, -80])
        plt.xlabel("Frequency (MHz)")
        plt.ylabel("Magnitude (dBFS)")
        plt.title("FFT Analysis")
        plt.grid()
        plt.show()

# Example Usage
if __name__ == "__main__":
    # Read waveforms
    waveform_reader = ReadWaveforms(
        ip="10.73.137.111",
        afe=4,
        ch=4,
        samples=1000,
        plot=True
    )

    # Perform FFT analysis
    fft_analysis = FFTAnalysis(
        signal=waveform_reader.waveform,
        sampling_rate=1/16e-9,
        plot=True
    )