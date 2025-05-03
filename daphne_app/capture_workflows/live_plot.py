from __future__ import annotations

"""
Interactive waveform viewer

CLI wrapper around ivtools.Daphne.read_reg that plots N loops of spy-
buffer reads for a list of AFEs & channels.  All parameters are supplied
by the Typer command below.
"""

from typing import Sequence, List
import time
import numpy as np
import matplotlib.pyplot as plt
from rich.console import Console

from ..hardware.daphne import Daphne
from ..utils.colors  import RED
from ..utils.ip_utils  import endpoint_ip

console = Console()


_COLORS = [
    "tab:blue", "tab:orange", "tab:green", "tab:red",
    "tab:purple", "tab:brown", "tab:gray", "tab:olive",
]

# ----------------------------------------------------------------------
# Public shim expected by the Typer CLI
# ----------------------------------------------------------------------
def run(ip_suffix: int, afe: int, ch: int, samples: int) -> None:  # noqa: D401
    """
    Thin adapter so that *cli.py* can keep calling ``live_plot.run``.

    • converts the single-AFE / single-channel request into the lists that
      :func:`view` expects
    • derives an integer `loops` value (50-word bursts) and keeps the read
      size at 50 words for maximum throughput
    """
    if samples % 50:
        raise ValueError("--samples must be a multiple of 50 for live mode")

    loops = samples // 50
    view(
        ip_suffix        = ip_suffix,
        afes             = [afe],
        channels         = [ch],
        loops            = loops,
        samples_per_read = 50,
        do_trigger       = True,
    )



def view(
    ip_suffix: int,
    afes: Sequence[int],
    channels: Sequence[int],
    loops: int,
    samples_per_read: int,
    do_trigger: bool,
) -> None:
    """
    Display waveforms live in a matplotlib figure.

    Parameters
    ----------
    ip_suffix : int
        Board suffix (107 → 7, etc.).
    afes, channels : list[int]
        Which AFEs (0-4) and channels (0-39) to plot.
        Typical use: channels 0-7 so one colour per ch.
    loops : int
        Number of *50-word* reads to concatenate per channel.
        20 loops × 50 words = 1 000 samples.
    samples_per_read : int
        Words per single read_reg call (>=1 and <=50).
        Keep 50 for max speed.
    do_trigger : bool
        Issue spy-buffer SW trigger before each capture.
    """
    ip  = endpoint_ip(ip_suffix)
    nch = len(channels)
    na  = len(afes)

    # dynamic subplot grid
    if na == 1:
        nrows, ncols, figsize = 1, 1, (7, 5)
    elif na == 2:
        nrows, ncols, figsize = 1, 2, (14, 5)
    elif na == 3:
        nrows, ncols, figsize = 1, 3, (16.5, 4)
    else:
        ncols = 3
        nrows = (na + 2) // 3
        figsize = (16, 9)

    plt.ion()
    fig, axes = plt.subplots(nrows, ncols, figsize=figsize,
                             sharex=False, sharey=False)
    axes = np.atleast_1d(axes).flatten()

    base   = 0x40000000
    step_a = 0x100000
    step_c = 0x10000

    try:
        dev = Daphne(ip)
        console.print(f"[cyan]Reading spy buffers from {ip}[/]")

        for idx, afe in enumerate(afes):
            ax = axes[idx]
            ax.set_title(f"AFE{afe}", fontsize=10)
            ax.set_xlabel("Samples", fontsize=8)
            if idx % ncols == 0:
                ax.set_ylabel("14-bit data", fontsize=8)
            for spine in ("top", "right"):
                ax.spines[spine].set_visible(False)

            # capture
            chans_data: List[np.ndarray] = [np.empty(0, dtype=np.uint16)
                                            for _ in channels]

            if do_trigger:
                dev.write_reg(0x2000, [1234])

            t0 = time.time()
            for _ in range(loops):
                for ci, ch in enumerate(channels):
                    addr = base + step_a * afe + step_c * ch
                    raw  = dev.read_reg(addr, samples_per_read)
                    chans_data[ci] = np.append(
                        chans_data[ci],
                        np.array(raw[2:], dtype=np.uint16),
                    )
            console.print(f"  AFE{afe}: captured "
                          f"{loops*samples_per_read} samples in "
                          f"{time.time()-t0:.2f}s")

            # plot
            for ci, ch in enumerate(channels):
                col = _COLORS[ci % len(_COLORS)]
                ax.plot(chans_data[ci], linewidth=0.5,
                        color=col, label=f'ch {ch}')
            ax.legend(loc="lower right", fontsize="xx-small",
                      framealpha=0.5)

        plt.tight_layout()
        plt.show(block=False)
        console.print(f"[green]Waveforms displayed – close the figure to exit[/]")
        plt.ioff()
        plt.show()

    except Exception as exc:                            # noqa: BLE001
        console.print(f"[{RED}]Error: {exc}[/]")

    finally:
        try:
            dev.close()
        except Exception:  # device may not exist if earlier error
            pass
