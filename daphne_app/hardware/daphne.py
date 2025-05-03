# daphne_app/hardware/daphne.py
"""
Light-weight client for the DAPHNE UDP register protocol
========================================================

Only the NumPy names that are *actually* used are imported; everything
else relies on ``numpy as np``.
"""

from __future__ import annotations

# ───────────────────────────── stdlib ───────────────────────────────
import logging
import re
import socket
import struct
import unicodedata
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from functools import wraps
from time import sleep
from typing import Iterable, Sequence

# ────────────────────────── 3rd-party ───────────────────────────────
import matplotlib.pyplot as plt
import numpy as np

# ─────────────────────────── logging ────────────────────────────────
logger = logging.getLogger(__name__)

# ─────────────────────────── helpers ────────────────────────────────
def timeout_handler(func):
    """
    Decorator that kills the wrapped function after **1 s**.
    Works for both the main and worker threads.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        timeout = 1  # seconds
        with ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(func, *args, **kwargs)
            try:
                return fut.result(timeout=timeout)
            except FuturesTimeoutError:  # pragma: no cover
                raise TimeoutError(
                    "Operation timed out – check cabling / IP / command."
                ) from None

    return wrapper


def _remove_control_chars(s: str) -> str:
    """Strip ASCII control codes – keeps output printable."""
    return "".join(ch for ch in s if unicodedata.category(ch)[0] != "C")


# ──────────────────────────── class ─────────────────────────────────
class Daphne:
    """
    Thin UDP client for the DAPHNE firmware.

    All low-level I/O is performed through *read_/write_reg* and
    *read_/write_fifo*; everything else builds on top.
    """

    # ── setup / teardown ────────────────────────────────────────────
    def __init__(self, ipaddr: str, port: int = 2001):
        self.ipaddr = ipaddr
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.target = (ipaddr, port)

    def close(self) -> None:
        self.sock.close()

    def reset_socket(self) -> None:
        logger.info("Resetting UDP socket to %s:%d", *self.target)
        self.close()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # ── low-level primitives ───────────────────────────────────────
    @timeout_handler
    def read_reg(self, addr: int, size: int) -> tuple[int, ...]:
        cmd = struct.pack("BB", 0x00, size) + struct.pack("<Q", addr)
        try:
            self.sock.sendto(cmd, self.target)
            raw, _ = self.sock.recvfrom(2 + 8 * size)
            return struct.unpack(f"<BB{size}Q", raw)
        except Exception as exc:  # pragma: no cover  – network-side
            logger.error("read_reg(%#x): %s", addr, exc)
            self.reset_socket()
            raise

    @timeout_handler
    def write_reg(self, addr: int, data: Sequence[int]) -> None:
        cmd = (
            struct.pack("BB", 0x01, len(data))
            + struct.pack("<Q", addr)
            + b"".join(struct.pack("<Q", w) for w in data)
        )
        try:
            self.sock.sendto(cmd, self.target)
        except Exception as exc:  # pragma: no cover
            logger.error("write_reg(%#x): %s", addr, exc)
            self.reset_socket()
            raise

    @timeout_handler
    def read_fifo(self, addr: int, size: int) -> tuple[int, ...]:
        cmd = struct.pack("BB", 0x08, size) + struct.pack("<Q", addr)
        try:
            self.sock.sendto(cmd, self.target)
            raw, _ = self.sock.recvfrom(2 + 8 * size)
            return struct.unpack(f"<BB{size}Q", raw)
        except Exception as exc:  # pragma: no cover
            logger.error("read_fifo(%#x): %s", addr, exc)
            self.reset_socket()
            raise

    @timeout_handler
    def write_fifo(self, addr: int, data: Iterable[int]) -> None:
        payload = b"".join(struct.pack("<Q", w) for w in data)
        cmd = struct.pack("BB", 0x09, len(data)) + struct.pack("<Q", addr) + payload
        try:
            self.sock.sendto(cmd, self.target)
        except Exception as exc:  # pragma: no cover
            logger.error("write_fifo(%#x): %s", addr, exc)
            self.reset_socket()
            raise

    # ── higher-level helpers ───────────────────────────────────────
    def command(self, text: str) -> str:
        """Send an ASCII command terminated by <CR> and return the reply."""
        bytes_ = [ord(c) for c in text] + [0x0D]
        for i in range(0, len(bytes_), 50):
            self.write_fifo(0x9000_0000, bytes_[i : i + 50])
        return self._read_command_reply()

    # ----------------------------------------------------------------
    # ASCII reply parser
    # ----------------------------------------------------------------
    def _read_command_reply(self) -> str:
        """
        Read ASCII reply until the FIFO is *really* empty.
        A reply ends with one or more 0xFF words; we return after seeing the
        terminator **and** three consecutive empty reads.
        """
        out: list[str] = []
        seen_end   = False
        empty_reads = 0

        while empty_reads < 3:                       # max ≈ 3 × 5 ms
            words = self.read_fifo(0x9000_0000, 50)[2:]
            payload = [w for w in words if w != 0xFF]   # strip padding

            if not payload:
                empty_reads += 1
            else:
                empty_reads = 0                        # still receiving data

            for w in payload:
                if w in (1, 2, 3):                    # START/RESULT/END tags
                    out.append(f"[{['START','RESULT','END'][w-1]}]")
                else:
                    ch = chr(w & 0xFF)
                    if ch.isprintable():
                        out.append(ch)

            seen_end |= 0xFF in words
            if seen_end and empty_reads >= 3:
                break

            sleep(0.005)

        return _remove_control_chars("".join(out))
    # ----------------------------------------------------------------
    # Convenience “lab helpers”
    # ----------------------------------------------------------------
    _CM_RE = re.compile(r"Voltage\(mV\)=\s*([-+]?\d+\.?\d*)")

    def read_current(self, ch: int = 0, iterations: int = 3, retries: int = 50) -> float:
        """Return the *average* current (mV) across *iterations* reads."""
        pattern = re.compile(rf"CM CH = {ch} Voltage\(mV\)=\s*([-+]?\d+\.?\d*)")
        for _ in range(retries):
            try:
                values = [
                    float(m)
                    for _ in range(iterations)
                    for m in pattern.findall(self.command(f"RD CM CH {ch}"))
                ]
                if values:
                    return float(np.mean(values))
            except Exception as exc:  # pragma: no cover – mostly network
                logger.debug("read_current retry: %s", exc)
                self.reset_socket()
        raise RuntimeError(f"Could not read current for channel {ch}")

    # ----------------------------------------------------------------
    # Spy-buffer helpers / DSP
    # ----------------------------------------------------------------
    def read_waveform(
        self,
        afe: int,
        ch: int,
        samples: int = 1000,
        *,
        plot: bool = False,
        self_trigger: bool = False,
        save_path: str | None = None,
    ) -> np.ndarray:
        """Capture *samples* words from one channel."""
        if self_trigger:
            self.write_reg(0x2000, [1234])

        base = 0x4000_0000 + 0x100_000 * afe + 0x10_000 * ch
        data: list[int] = []
        for i in range(samples // 50):
            addr = base + 50 * i
            data.extend(self.read_reg(addr, 50)[2:])

        wf = np.asarray(data, dtype=np.uint16)

        if plot:
            self._plot_waveform(wf, afe, ch, save_path)
        return wf

    # ---- plotting helpers -----------------------------------------
    @staticmethod
    def _plot_waveform(wf: np.ndarray, afe: int, ch: int, path: str | None) -> None:
        t = np.linspace(0.0, len(wf) * 16e-9, len(wf))
        plt.figure(figsize=(10, 4))
        plt.plot(t, wf, lw=0.7, label=f"AFE {afe} CH {ch}")
        plt.xlabel("Time [s]")
        plt.ylabel("ADC counts")
        plt.title("Spy-buffer waveform")
        plt.grid(True)
        plt.legend()
        if path:
            plt.savefig(path, dpi=300)
            logger.info("Waveform plot saved to %s", path)
        else:
            plt.show()

    # ---- FFT helpers ----------------------------------------------
    @staticmethod
    def compute_fft(
        signal: np.ndarray,
        *,
        dt: float = 16e-9,
        plot: bool = False,
        save_path: str | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return positive-freq FFT in dBFS."""
        n = signal.size

        # full FFT, normalised
        fft_full = np.fft.fft(signal) / n          # complex
        freq     = np.fft.fftfreq(n, d=dt)         # Hz

        # keep *strictly* positive frequencies only
        mask = freq > 0
        x = freq[mask] / 1e6                       # → MHz
        y = 20 * np.log10(
            np.abs(2 * fft_full[mask]) / 2**14    # *2 for single-sided FFT
            + 1e-20                               # tiny guard vs log10(0)
        )

        if plot:
            plt.figure(figsize=(9, 4))
            plt.plot(x, y, lw=0.7)
            plt.xscale("log")
            plt.ylim([-140, -80])
            plt.xlabel("Frequency [MHz]")
            plt.ylabel("Magnitude [dBFS]")
            plt.title("FFT")
            plt.grid(True, which="both")
            if save_path:
                plt.savefig(save_path, dpi=300)
                logger.info("FFT plot saved to %s", save_path)
            else:
                plt.show()

        return x, y

    # ---- statistics helpers ---------------------------------------
    @staticmethod
    def compute_mean_fft(
        waveforms: Sequence[np.ndarray],
        *,
        dt: float = 16e-9,
    ) -> tuple[np.ndarray, np.ndarray, float]:
        """Average several FFTs and return (freq, mag, rms)."""
        ffts, rms, xs = [], [], None
        for wf in waveforms:
            if wf.size == 0:
                continue
            x, y = Daphne.compute_fft(wf, dt=dt)
            ffts.append(y)
            rms.append(float(np.std(wf)))
            xs = x
        if not ffts:
            raise ValueError("No non-empty waveforms passed")
        mean_y = np.mean(ffts, axis=0)
        return xs, mean_y, float(np.mean(rms))
