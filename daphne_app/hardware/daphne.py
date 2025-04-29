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
import re
from numpy import mean
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from functools import wraps, lru_cache
import matplotlib.pyplot as plt

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


class Daphne:
    def __init__(self, ipaddr, port=2001):
        self.ipaddr = ipaddr
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.target = (ipaddr, port)

    def reset_socket(self):
        """
        Resets the socket connection to ensure a clean state.
        """
        logger.info("Resetting socket connection...")
        self.sock.close()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.target = (self.ipaddr, self.port)

    @timeout_handler
    def read_reg(self, addr, size):
        cmd = struct.pack("BB", 0x00, size) + struct.pack("Q", addr)
        try:
            self.sock.sendto(cmd, self.target)
            d, _ = self.sock.recvfrom(2 + (8 * size))
            return struct.unpack(f"<BB{size}Q", d)
        except Exception as e:
            logger.error(f"Error reading register: {e}")
            self.reset_socket()  # Reset socket in case of failure
            raise e

    @timeout_handler
    def write_reg(self, addr, data):
        cmd = struct.pack("BB", 1, len(data)) + struct.pack("Q", addr)
        cmd += b"".join(struct.pack("Q", i) for i in data)
        try:
            self.sock.sendto(cmd, self.target)
        except Exception as e:
            logger.error(f"Error writing register: {e}")
            self.reset_socket()  # Reset socket in case of failure
            raise e

    @timeout_handler
    def read_fifo(self, addr, size):
        cmd = struct.pack("BB", 0x08, size) + struct.pack("Q", addr)
        try:
            self.sock.sendto(cmd, self.target)
            d, _ = self.sock.recvfrom(2 + (8 * size))
            return struct.unpack(f"<BB{size}Q", d)
        except Exception as e:
            logger.error(f"Error reading FIFO: {e}")
            self.reset_socket()  # Reset socket in case of failure
            raise e

    @timeout_handler
    def write_fifo(self, addr, data):
        cmd = struct.pack("BB", 0x09, len(data)) + struct.pack("Q", addr)
        cmd += b"".join(struct.pack("Q", i) for i in data)
        try:
            self.sock.sendto(cmd, self.target)
        except Exception as e:
            logger.error(f"Error writing FIFO: {e}")
            self.reset_socket()  # Reset socket in case of failure
            raise e

    def close(self):
        self.sock.close()

    @lru_cache(maxsize=128)
    def command(self, cmd_string):
        cmd_bytes = [ord(ch) for ch in cmd_string] + [0x0D]
        for i in range(0, len(cmd_bytes), 50):
            self.write_fifo(0x90000000, cmd_bytes[i:i + 50])
        return self.get_response_data()
        # def command(self, cmd_string):
        #     """
        #     Sends a command to the hardware and returns the response data.
        #     Temporarily modified to print all received data for debugging.
        #     """
        #     cmd_bytes = [ord(ch) for ch in cmd_string] + [0x0D]
        #     for i in range(0, len(cmd_bytes), 50):
        #         self.write_fifo(0x90000000, cmd_bytes[i:i + 50])

        #     # Collect and print raw response data
        #     response = self.get_response_data()
        #     print("Raw Response:", response)  # Print raw response for analysis
        #     logger.info(f"Raw Response: {response}")  # Log it as well
        #     return response

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
            sleep(0.005)
            retry_count -= 1

        return self.remove_control_characters("".join(response))

    def read_current(self, ch=0, iterations=3, max_retries=50):
        """
        Reads the current for a specific channel using regular expressions for parsing.
        Args:
            ch (int): Channel number.
            iterations (int): Number of readings to average.
            max_retries (int): Maximum number of retries before failing.
        Returns:
            float: Mean current value across iterations.
        Raises:
            RuntimeError: If no valid reading is obtained after retries.
        """


        # Regex pattern to match the voltage value in the response
        current_pattern = re.compile(rf"CM CH = {ch} Voltage\(mV\)=\s*([-+]?\d*\.\d+|\d+)")

        # Retry mechanism
        for attempt in range(max_retries):
            try:
                # logger.info(f"Attempt {attempt + 1}: Reading current for channel {ch}...")
                currents = []
                for _ in range(iterations):
                    # Send the command and get the response
                    response = self.command(f"RD CM CH {ch}")
                    # logger.info(f"Response: {response}")

                    # Use regex to find the current value
                    matches = current_pattern.findall(response)
                    if matches:
                        for match in matches:
                            current_value = float(match)
                            currents.append(current_value)
                            # logger.info(f"Parsed current value: {current_value} mA")

                # If valid currents are collected, return their mean
                if currents:
                    # logger.info(f"Collected currents: {currents}")
                    return mean(currents)

            except Exception as e:
                logger.warning(f"Failed to read current on attempt {attempt + 1}: {e}")
                self.reset_socket()  # Reset the socket if an error occurs

        # If retries are exhausted, close the connection and raise an error
        self.close()
        raise RuntimeError(f"Failed to read current for channel {ch} after {max_retries} attempts")

    def read_current_dep(self, ch=0,iterations=3):
        self.current = None
        counter=0
        while self.current is None and counter<50:
            try:
                self.current = [float(self.command(f'RD CM CH {ch}').split("(mV)= ")[1][:8]) for i in range (iterations)]
                counter+=1
            except:
                if counter>=50:
                    self.close()
                else:
                    pass
        return mean(self.current)

    def read_bias(self):
        """
        Reads all variables from the response and returns them as a dictionary.
        Returns:
            dict: Dictionary of all variables and their corresponding values.
        Raises:
            ValueError: If no valid variables are found in the response.
        """
        # Send the command and get the response
        response = self.command("RD VM ALL")
        logger.info(f"Response: {response}")

        # Regex to extract all key-value pairs, including POWER and TEMP
        # Enhanced regex pattern to ensure all expected variables are captured
        variable_pattern = re.compile(r"(VBIAS[0-4]|POWER\([-+a-zA-Z0-9.]+\)|TEMP\([a-zA-Z]+\))=\s*([\d.\-]+)")
        matches = variable_pattern.findall(response)

        if matches:
            # Convert matches to a dictionary
            variables = {key: float(value) for key, value in matches}
            logger.info(f"Extracted variables: {variables}")
            return variables

        # Raise an error if no valid matches are found
        raise ValueError("Failed to extract variables from response.")

    @staticmethod
    def remove_control_characters(s):
        return "".join(ch for ch in s if unicodedata.category(ch)[0] != "C")

    def read_waveform(self, afe, ch, samples=1000, plot=False, save_path=None):
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
            self._plot_waveform(wf, afe, ch, save_path)

        return wf

    def _plot_waveform(self, wf, afe, ch, save_path=None):
        time_axis = np.linspace(0.0, len(wf) * 16e-9, num=len(wf))
        plt.figure(figsize=(10, 5))
        plt.plot(time_axis, wf, linewidth=0.6, label=f"AFE {afe} CH {ch}")
        plt.xlabel("Time (s)")
        plt.ylabel("Amplitude")
        plt.title(f"Waveform for AFE {afe}, Channel {ch}")
        plt.legend()
        plt.grid()

        if save_path:
            plt.savefig(save_path, dpi=300)
            logger.info(f"Waveform plot saved to {save_path}")
        else:
            plt.show()

    @staticmethod
    def compute_fft(signal, dt=16e-9, plot=False, save_path=None):
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

            if save_path:
                plt.savefig(save_path, dpi=300)
                logger.info(f"FFT plot saved to {save_path}")
            else:
                plt.show()

        return x, y

    @staticmethod
    def compute_mean_fft(waveforms, label, plot=False, save_path=None):
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

            if save_path:
                plt.savefig(save_path, dpi=300)
                logger.info(f"Mean FFT plot saved to {save_path}")
            else:
                plt.show()

        return mean_x, mean_y, mean_rms


    def compute_fft_for_channels(self, afe, channels, samples=1000, dt=16e-9, plot=False, save_path=None):
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
            self._plot_ffts_for_channels(fft_results, afe, save_path)

        return fft_results

    def _plot_ffts_for_channels(self, fft_results, afe, save_path=None):
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

        if save_path:
            plt.savefig(save_path, dpi=300)
            logger.info(f"FFT plots for channels saved to {save_path}")
        else:
            plt.show()

    @staticmethod
    def compare_ffts_across_ips_and_channels(ips, afe, channels, samples=1000, dt=16e-9, repeats=20, plot=True, save_path=None):
        """
        Compares the mean FFTs for multiple channels across multiple IP addresses.
        """
        fft_results = {}

        for ip in ips:
            logger.info(f"Processing IP: {ip}")
            device = Daphne(ip)

            ip_results = {}
            for ch in channels:
                waveforms = []
                for _ in range(repeats):
                    wf = device.read_waveform(afe=afe, ch=ch, samples=samples)
                    if wf.any():
                        waveforms.append(wf)
                    else:
                        logger.warning(f"Empty waveform for IP {ip}, AFE {afe}, CH {ch}")

                if waveforms:
                    x, y, rms = device.compute_mean_fft(waveforms, label=f"IP {ip} CH {ch}")
                    ip_results[ch] = (x, y, rms)
                else:
                    logger.warning(f"No valid waveforms collected for IP {ip}, CH {ch}")

            fft_results[ip] = ip_results

        if plot:
            Daphne._plot_ffts_across_ips_and_channels(fft_results, afe, save_path)

        return fft_results

    @staticmethod
    def _plot_ffts_across_ips_and_channels(fft_results, afe, save_path=None):
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

        if save_path:
            plt.savefig(save_path, dpi=300)
            logger.info(f"FFT comparison plot saved to {save_path}")
        else:
            plt.show()

    def _compute_mean_fft_from_waveforms(self, waveforms, dt):
        """
        Computes the mean FFT from multiple waveforms.
        Args:
            waveforms (list of np.ndarray): List of waveforms.
            dt (float): Time interval between samples.
        Returns:
            tuple: Mean FFT (x, y) and RMS value of the waveforms.
        """
        fft_x = []
        fft_y = []
        rms_list = []

        for wf in waveforms:
            x, y = self.compute_fft(wf, dt=dt)
            fft_x.append(x)
            fft_y.append(y)
            rms_list.append(std(wf))

        # Compute mean FFT and RMS
        mean_x = np.mean(fft_x, axis=0)
        mean_y = np.mean(fft_y, axis=0)
        mean_rms = np.round(np.mean(rms_list), 3)

        return mean_x, mean_y, mean_rms

    def _plot_mean_ffts_for_channels(self, mean_fft_results, afe, save_path=None):
        """
        Plots the mean FFT for multiple channels.
        Args:
            mean_fft_results (dict): Dictionary with channel numbers as keys and FFT results (x, y, rms) as values.
            afe (int): AFE number.
            save_path (str): Path to save the plot. If None, displays the plot.
        """
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

        if save_path:
            plt.savefig(save_path, dpi=300)
            logger.info(f"Mean FFT plots saved to {save_path}")
        else:
            plt.show()

    def compute_mean_fft_for_channels(self, afe, channels, samples=1000, repeats=20, dt=16e-9, plot=False, save_path=None):
        """
        Computes the mean FFT across multiple waveforms for a collection of channels.
        Args:
            afe (int): AFE number.
            channels (list of int): List of channels to analyze.
            samples (int): Number of samples per waveform.
            repeats (int): Number of waveforms to collect per channel.
            dt (float): Time interval between samples.
            plot (bool): Whether to plot the mean FFTs for all channels.
            save_path (str): Path to save the plot. If None, displays the plot.
        Returns:
            dict: Dictionary with channel numbers as keys and mean FFT results (x, y, rms) as values.
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

        # Use ThreadPoolExecutor to process channels in parallel
        with ThreadPoolExecutor() as executor:
            results = executor.map(process_channel, channels)

        for ch, result in results:
            if result:
                mean_fft_results[ch] = result

        if plot:
            self._plot_mean_ffts_for_channels(mean_fft_results, afe, save_path)

        return mean_fft_results
