"""
Optimized library for communicating with specific hardware in Daphne
"""
from time import sleep
from numpy import mean, std, fft as np_fft, log10
import numpy as np
import socket
import struct
import unicodedata
import signal
import logging
from concurrent.futures import ThreadPoolExecutor
import matplotlib.pyplot as plt
from functools import lru_cache


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from functools import wraps


def timeout_handler(func):
    """
    Decorator to enforce a timeout on a function.
    Works for both main thread and worker threads.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        timeout = 1  # Timeout in seconds
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            try:
                return future.result(timeout=timeout)
            except FuturesTimeoutError:
                raise TimeoutError("Operation timed out. Check device connection or command validity.")
    return wrapper


def signal_handler(signum, frame):
    raise TimeoutError("Operation timed out. Check device connection or command validity.")


# def timeout_handler(func):
#     def wrapper(*args, **kwargs):
#         signal.signal(signal.SIGALRM, signal_handler)
#         signal.alarm(1)
#         try:
#             result = func(*args, **kwargs)
#         finally:
#             signal.alarm(0)
#         return result
#     return wrapper


class Daphne:
    def __init__(self, ipaddr, port=2001):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.target = (ipaddr, port)

    @timeout_handler
    def read_reg(self, addr, size):
        cmd = struct.pack("BB", 0x00, size) + struct.pack("Q", addr)
        self.sock.sendto(cmd, self.target)
        d, _ = self.sock.recvfrom(2 + (8 * size))
        return struct.unpack(f"<BB{size}Q", d)

    @timeout_handler
    def write_reg(self, addr, data):
        cmd = struct.pack("BB", 1, len(data)) + struct.pack("Q", addr)
        cmd += b"".join(struct.pack("Q", i) for i in data)
        self.sock.sendto(cmd, self.target)

    @timeout_handler
    def read_fifo(self, addr, size):
        cmd = struct.pack("BB", 0x08, size) + struct.pack("Q", addr)
        self.sock.sendto(cmd, self.target)
        d, _ = self.sock.recvfrom(2 + (8 * size))
        return struct.unpack(f"<BB{size}Q", d)

    @timeout_handler
    def write_fifo(self, addr, data):
        cmd = struct.pack("BB", 0x09, len(data)) + struct.pack("Q", addr)
        cmd += b"".join(struct.pack("Q", i) for i in data)
        self.sock.sendto(cmd, self.target)

    def close(self):
        self.sock.close()

    @lru_cache(maxsize=128)
    def command(self, cmd_string):
        cmd_bytes = [ord(ch) for ch in cmd_string] + [0x0D]
        for i in range(0, len(cmd_bytes), 50):
            self.write_fifo(0x90000000, cmd_bytes[i:i + 50])
        return self.get_response_data()

    def get_response_data(self):
        response = []
        retry_count = 40

        while retry_count > 0:
            response_bytes = self.read_fifo(0x90000000, 50)
            for b in response_bytes[2:]:
                if b == 255:  # End of data
                    break
                elif b in (1, 2, 3):  # Control characters
                    response.append(f"[{['START', 'RESULT', 'END'][b - 1]}]")
                elif chr(b).isprintable():
                    response.append(chr(b))
            sleep(0.002)
            retry_count -= 1

        return self.remove_control_characters("".join(response))

    def read_current(self, ch=0, iterations=3):
        for _ in range(50):
            try:
                currents = [
                    float(self.command(f"RD CM CH {ch}").split("(mV)= ")[1][:8])
                    for _ in range(iterations)
                ]
                return mean(currents)
            except Exception:
                sleep(0.1)  # Backoff on failure
        self.close()
        raise RuntimeError("Failed to read current after multiple attempts")

    def read_bias(self):
        info = self.command("RD VM ALL")
        return [float(info.split(f"VBIAS{i}=")[1][:6]) for i in range(5)]

    @staticmethod
    def remove_control_characters(s):
        return "".join(ch for ch in s if unicodedata.category(ch)[0] != "C")

    def read_waveform(self, afe, ch, samples=1000, plot=False):
        """
        Reads waveforms from a specific AFE and channel on the device.
        """
        self.write_reg(0x2000, [1234])  # Trigger spy buffers
        wf = []
        try:
            base_addr = 0x40000000 + (0x100000 * afe) + (0x10000 * ch)
            for i in range(samples // 50):
                addr = base_addr + (i * 50)
                chunk = self.read_reg(addr, 50)[2:]  # Skip metadata bytes
                wf.extend(chunk)
        except Exception as e:
            logger.error(f"Error reading waveform for AFE {afe}, Channel {ch}: {e}")

        wf = np.array(wf)
        if wf.size == 0 or not wf.any():
            logger.warning(f"Empty or zero waveform for AFE {afe}, Channel {ch}.")

        if plot:
            self._plot_waveform(wf, afe, ch)

        return wf

    def _plot_waveform(self, wf, afe, ch):
        time_axis = np.linspace(0.0, len(wf) * 16e-9, num=len(wf))
        plt.figure(figsize=(10, 5))
        plt.plot(time_axis, wf, linewidth=0.6, label=f"AFE {afe} CH {ch}")
        plt.xlabel("Time (s)")
        plt.ylabel("Amplitude")
        plt.title(f"Waveform for AFE {afe}, Channel {ch}")
        plt.legend()
        plt.grid()
        plt.show()

    @staticmethod
    def compute_fft(signal, dt=16e-9, plot=False):
        """
        Computes and optionally plots the FFT of a signal.
        """
        t = np.arange(0, signal.shape[-1]) * dt
        sigFFT = np_fft.fft(signal) / t.shape[0]
        freq = np_fft.fftfreq(t.shape[0], d=dt)
        firstNegInd = np.argmax(freq < 0)
        freqAxisPos = freq[:firstNegInd]
        sigFFTPos = 2 * sigFFT[:firstNegInd]

        x = freqAxisPos / 1e6  # Convert to MHz
        y = 20 * log10(np.abs(sigFFTPos) / 2**14)

        if plot:
            plt.figure(figsize=(10, 5))
            plt.plot(x, y, linewidth=0.6)
            plt.xlabel("Frequency (MHz)")
            plt.ylabel("Magnitude (dBFS)")
            plt.title("FFT Analysis")
            plt.ylim([-140, -80])
            plt.xscale("log")
            plt.grid()
            plt.show()

        return x, y

    @staticmethod
    def compute_mean_fft(waveforms, label, plot=False):
        """
        Computes and optionally plots the mean FFT of multiple waveforms.
        """
        fft_x, fft_y = [], []
        rms_list = []

        for wf in waveforms:
            if not wf.any():
                logger.warning("Skipping empty or zero signal.")
                continue

            x, y = Daphne.compute_fft(wf)
            fft_x.append(x)
            fft_y.append(y)
            rms_list.append(std(wf))

        if not fft_x or not fft_y:
            raise ValueError("No valid FFT data to compute mean.")

        mean_x = np.mean(fft_x, axis=0)
        mean_y = np.mean(fft_y, axis=0)
        mean_rms = np.round(np.mean(rms_list), 3)

        if plot:
            plt.figure(figsize=(10, 7))
            plt.plot(mean_x, mean_y, linewidth=1, label=f"{label} \t RMS={mean_rms}".expandtabs())
            plt.ylim([min(mean_y) - 10, -80])
            plt.xscale("log")
            plt.ylabel("dBFS")
            plt.xlabel("MHz")
            plt.title("Mean FFT Analysis")
            plt.legend()
            plt.tight_layout()
            plt.show()

        return mean_x, mean_y, mean_rms

    def compute_fft_for_channels(self, afe, channels, samples=1000, dt=16e-9, plot=False):
        """
        Computes FFTs for multiple channels and optionally plots them.
        """
        fft_results = {}

        for ch in channels:
            logger.info(f"Processing channel {ch}...")
            wf = self.read_waveform(afe, ch, samples)
            if wf.any():
                x, y = self.compute_fft(wf, dt=dt)
                fft_results[ch] = (x, y)
            else:
                logger.warning(f"No valid data for channel {ch}. Skipping.")

        if plot:
            self._plot_ffts_for_channels(fft_results, afe)

        return fft_results

    def _plot_ffts_for_channels(self, fft_results, afe):
        plt.figure(figsize=(12, 8))
        for ch, (x, y) in fft_results.items():
            plt.plot(x, y, label=f"AFE {afe} CH {ch}")
        plt.xlabel("Frequency (MHz)")
        plt.ylabel("Magnitude (dBFS)")
        plt.title("FFT Analysis for Multiple Channels")
        plt.ylim([-140, -80])
        plt.xscale("log")
        plt.grid()
        plt.legend(loc="upper right", fontsize="small")
        plt.tight_layout()
        plt.show()

    def compute_mean_fft_for_channels(self, afe, channels, samples=1000, repeats=20, dt=16e-9, plot=False):
        """
        Computes the mean FFT across multiple waveforms for a collection of channels.
        """
        mean_fft_results = {}

        def process_channel(ch):
            waveforms = []
            for _ in range(repeats):
                wf = self.read_waveform(afe, ch, samples)
                if wf.any():
                    waveforms.append(wf)
            if waveforms:
                return ch, self._compute_mean_fft_from_waveforms(waveforms, dt)
            logger.warning(f"No valid waveforms collected for Channel {ch}. Skipping.")
            return ch, None

        with ThreadPoolExecutor() as executor:
            results = executor.map(process_channel, channels)

        for ch, result in results:
            if result:
                mean_fft_results[ch] = result

        if plot:
            self._plot_mean_ffts_for_channels(mean_fft_results, afe)

        return mean_fft_results

    def _compute_mean_fft_from_waveforms(self, waveforms, dt):
        fft_x = []
        fft_y = []
        rms_list = []

        for wf in waveforms:
            x, y = self.compute_fft(wf, dt=dt)
            fft_x.append(x)
            fft_y.append(y)
            rms_list.append(std(wf))

        mean_x = np.mean(fft_x, axis=0)
        mean_y = np.mean(fft_y, axis=0)
        mean_rms = np.round(np.mean(rms_list), 3)

        return mean_x, mean_y, mean_rms

    def _plot_mean_ffts_for_channels(self, mean_fft_results, afe):
        plt.figure(figsize=(12, 8))
        for ch, (x, y, rms) in mean_fft_results.items():
            plt.plot(x, y, label=f"AFE {afe} CH {ch} RMS={rms}")
        plt.xlabel("Frequency (MHz)")
        plt.ylabel("Magnitude (dBFS)")
        plt.title("Mean FFT Analysis for Multiple Channels")
        plt.ylim([-140, -80])
        plt.xscale("log")
        plt.grid()
        plt.legend(loc="upper right", fontsize="small")
        plt.tight_layout()
        plt.show()
    
    @staticmethod
    def compare_ffts_across_ips_and_channels(ips, afe, channels, samples=1000, dt=16e-9, repeats=20, plot=True):
        """
        Compares the mean FFTs for multiple channels across multiple IP addresses.
        """
        fft_results = {}

        for ip in ips:
            print(f"Processing IP: {ip}")
            device = Daphne(ip)  # Instantiate a new Daphne object for each IP

            ip_results = {}
            for ch in channels:
                waveforms = []
                for _ in range(repeats):
                    wf = device.read_waveform(afe=afe, ch=ch, samples=samples)
                    if wf.any():
                        waveforms.append(wf)
                    else:
                        print(f"Warning: Empty waveform for IP {ip}, AFE {afe}, CH {ch}")

                if waveforms:
                    x, y, rms = device.compute_mean_fft(waveforms, label=f"IP {ip} CH {ch}")
                    ip_results[ch] = (x, y, rms)
                else:
                    print(f"No valid waveforms collected for IP {ip}, CH {ch}.")

            fft_results[ip] = ip_results

        if plot:
            Daphne._plot_ffts_across_ips_and_channels(fft_results, afe)

        return fft_results

    @staticmethod
    def _plot_ffts_across_ips_and_channels(fft_results, afe):
        """
        Plots FFT comparisons for multiple IP addresses and channels.
        """
        plt.figure(figsize=(12, 8))
        for ip, channels in fft_results.items():
            for ch, (x, y, rms) in channels.items():
                plt.plot(x, y, label=f"{ip} CH {ch} RMS={rms}")
        plt.xlabel("Frequency (MHz)")
        plt.ylabel("Magnitude (dBFS)")
        plt.title(f"FFT Comparison for AFE {afe} Across Multiple IPs and Channels")
        plt.ylim([-140, -80])
        plt.xscale("log")
        plt.grid()
        plt.legend(loc="upper right", fontsize="small")
        plt.tight_layout()
        plt.show()