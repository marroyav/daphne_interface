from __future__ import annotations

"""
Write / read the analogue chain (offset DACs, gain, AFE regs, …).

Functions
---------
configure(ips, offsets=None, gains=None, only_indices=None, …)
    Write per-channel offsets and gains.
read(ips, only_indices=None, …)
    Read back offsets / gains and AFE register block.
"""

from collections.abc import Sequence
from typing import Iterable, List

import sys
from pathlib import Path
from daphne_app.hardware.daphne import Daphne
from rich.console import Console
from tqdm import tqdm

from daphne_app.utils.ip_utils import endpoint_ip
from daphne_app.utils.register_decode import pretty_print


console = Console()

# ──────────────────────────────────────────────────────────────────────
# helpers
# ──────────────────────────────────────────────────────────────────────


def _chk_len(name: str, arr: Sequence[int], expect: int) -> None:
    if len(arr) != expect:
        raise ValueError(f"{name} length {len(arr)} ≠ {expect}")


# ──────────────────────────────────────────────────────────────────────
# main public API
# ──────────────────────────────────────────────────────────────────────


def configure(
    ips: Iterable[int],
    *,
    offsets: Sequence[int] | None = None,
    gains: Sequence[int] | None = None,
    only_indices: Sequence[int] | None = None,
    progress: bool | str = "auto",
    offset_mv: int = 2250,
    gain: int = 1,
) -> None:
    """
    Write per-channel offset (mV) and coarse gain.

    Parameters
    ----------
    ips
        Iterable of endpoint suffixes (e.g. ``[7, 9]`` → 10.73.137.107 / 109).
    offsets
        mV list. If *None*, use ``offset_mv`` for every channel.
    gains
        Gain list. If *None*, use ``gain`` for every channel.
    only_indices
        If given, configure **only** these channel numbers instead of all 40.
    progress
        ``True`` | ``False`` or ``"auto"`` → tqdm only if stdout is a TTY.
    offset_mv, gain
        Defaults when *offsets* / *gains* are *None*.
    """
    all_indices: List[int] = list(range(40))
    only_indices = list(only_indices or all_indices)
    n_ch = len(only_indices)

    # build full-length vectors matching only_indices
    if offsets is None:
        offsets = [offset_mv] * n_ch
    if gains is None:
        gains = [gain] * n_ch

    _chk_len("offsets", offsets, n_ch)
    _chk_len("gains", gains, n_ch)

    # ── main loop per endpoint ───────────────────────────────────────
    for suffix in ips:
        full_ip = endpoint_ip(suffix)
        dev = Daphne(full_ip)

        # -- progress bar decision (avoids Daphne._tty look-up) ------
        if isinstance(progress, bool):
            use_tqdm = progress
        else:  # "auto"
            use_tqdm = sys.stdout.isatty()

        ch_iter = only_indices
        if use_tqdm:
            ch_iter = tqdm(ch_iter, desc=f"Channels {full_ip}", unit="ch")

        # -- write ---------------------------------------------------
        for ch_idx, ch in enumerate(ch_iter):
            off_val = offsets[ch_idx]
            gain_val = gains[ch_idx]
            dev.command(f"WR OFFSET CH {ch} V {off_val}")
            dev.command(f"CFG OFFSET CH {ch} GAIN {gain_val}")

        console.print(f"[green]Finished analog configuration on {full_ip}.[/]")


def read(
    ips: Iterable[int],
    *,
    only_indices: Sequence[int] | None = None,
) -> None:
    """
    Read back offset / gain plus three AFE register words.

    Printed in a table; uses `register_decode.pretty_print` for the
    per-register breakdown.
    """
    from rich.table import Table

    all_indices = list(range(40))
    indices = list(only_indices or all_indices)

    for suffix in ips:
        full_ip = endpoint_ip(suffix)
        dev = ivtools.Daphne(full_ip)
        console.rule(full_ip)

        # channel offsets -------------------------------------------------
        tbl = Table(title="Channel offsets")
        tbl.add_column("CH", justify="right")
        tbl.add_column("Offset", justify="right")
        tbl.add_column("Gain", justify="right")

        for ch in indices:
            off = dev.command(f"RD OFFSET CH {ch}", int)
            g = dev.command(f"RD OFFSET CH {ch} GAIN", int)
            tbl.add_row(f"{ch:02}", str(off), str(g))
        console.print(tbl)

        # AFE registers ---------------------------------------------------
        for afe in range(5):
            reg04 = dev.command(f"AFE {afe} RD 0x04", int)
            reg33 = dev.command(f"AFE {afe} RD 0x33", int)
            reg34 = dev.command(f"AFE {afe} RD 0x34", int)
            vgain = dev.command(f"AFE {afe} RD VGAIN", int)

            console.print(f"                        AFE{afe} registers")
            console.print(
                pretty_print(
                    {
                        0x04: reg04,
                        0x33: reg33,
                        0x34: reg34,
                        "VGAIN": vgain,
                    }
                )
            )
