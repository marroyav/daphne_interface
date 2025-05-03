# daphne_app/config_workflows/analog.py
from __future__ import annotations
"""
Write / read the analogue chain (offset DACs, coarse gain, VGA).

• configure(…) – offsets / gains / attenuators (VGAIN)
• read(…)      – dump everything in Rich tables

No dependency on *ivtools* any longer – we only use the in-package
`daphne_app.hardware.daphne.Daphne`.
"""

# ───────────────────────────────── standard / 3rd-party ──────────────────────────────
import re
import sys
from collections.abc import Iterable, Sequence
from typing import List

from rich.console import Console
from rich.table import Table
from tqdm import tqdm

# ─────────────────────────────────────  local  ───────────────────────────────────────
from daphne_app.hardware.daphne import Daphne
from daphne_app.utils.ip_utils import endpoint_ip
from daphne_app.utils.register_decode import pretty_print

console = Console()

# ───────────────────────── helpers ──────────────────────────


def _chk_len(name: str, arr: Sequence[int], expect: int) -> None:
    if len(arr) != expect:
        raise ValueError(f"{name} length {len(arr)} ≠ {expect}")


def _afe_set(indices: Sequence[int]) -> set[int]:
    """Return the *AFE* indices touched by *indices* (global CH numbers)."""
    return {ch // 8 for ch in indices}


# ──────────────────── regexes reused from analog_check.py ──────────────────
_OFFSET_PAT = re.compile(r"OFFSET DAC REG=\s*(\d+).*DAC GAIN=(\d+)")
_REG_PAT    = re.compile(r"REG\s*([0-9A-Fa-fx]+)\s*=\s*([0-9A-Fa-fx]+)")
_VGAIN_PAT  = re.compile(r"VGAIN DAC REG=\s*(\d+).*DAC GAIN=(\d+)")
_SPI_MAP    = {4: 0x04, 51: 0x33, 52: 0x34}

# ─────────────────────────── public API ────────────────────────────────────
def configure(
    ips: Iterable[int],
    *,
    offsets: Sequence[int] | None = None,
    gains: Sequence[int] | None = None,
    attenuators: Sequence[int] | None = None,   # AKA VGAIN
    vgains: Sequence[int] | None = None,        # compatibility alias
    only_indices: Sequence[int] | None = None,
    progress: bool | str = "auto",
    offset_mv: int = 2250,
    gain: int = 1,
    vgain: int = 0,
) -> None:
    """
    Configure OFFSET DACs, coarse gains and VGA attenuators.

    `attenuators` and `vgains` are synonyms so existing JSON files that
    carry `"attenuators"` work unchanged.
    """
    if attenuators is None:
        attenuators = vgains

    all_ch = list(range(40))
    only_indices = list(only_indices or all_ch)
    n_ch = len(only_indices)

    # vectors ----------------------------------------------------------------
    offsets = list(offsets) if offsets is not None else [offset_mv] * n_ch
    gains   = list(gains)   if gains   is not None else [gain]     * n_ch
    _chk_len("offsets", offsets, n_ch)
    _chk_len("gains",   gains,   n_ch)

    afe_used = sorted(_afe_set(only_indices))
    if attenuators is None:
        attenuators = [vgain] * len(afe_used)
    _chk_len("attenuators", attenuators, len(afe_used))
    vgain_map = dict(zip(afe_used, attenuators))

    # ------------------------------------------------------------------------
    for suf in ips:
        ip = endpoint_ip(suf)
        dev = Daphne(ip)

        use_bar = progress if isinstance(progress, bool) else sys.stdout.isatty()
        ch_iter = tqdm(only_indices, desc=f"Channels {ip}", unit="ch") if use_bar else only_indices

        # per-channel config
        for idx, ch in enumerate(ch_iter):
            dev.command(f"WR OFFSET CH {ch} V {offsets[idx]}")
            dev.command(f"CFG OFFSET CH {ch} GAIN {gains[idx]}")

        # per-AFE VGA
        for afe, v in vgain_map.items():
            dev.command(f"WR AFE {afe} VGAIN V {v}")

        console.print(f"[green]✓ Analog chain configured on {ip} (VGA={vgain_map})[/]")
        dev.close()


# ──────────────────────────────  reader  ──────────────────────────────────
def _parse_reg_val(text: str, pat: re.Pattern[str]) -> int | None:
    m = pat.search(text)
    return int(m.group(1)) if m else None


def read(
    ips: Iterable[int],
    *,
    only_indices: Sequence[int] | None = None,
) -> None:
    """
    Read back offsets / gains plus AFE register block (0x04, 0x33, 0x34, VGAIN).

    Everything is printed in Rich tables – no *ivtools* needed anymore.
    """
    all_ch = list(range(40))
    indices = list(only_indices or all_ch)

    for suf in ips:
        ip = endpoint_ip(suf)
        dev = Daphne(ip)
        console.rule(ip)

        # ── channel table ────────────────────────────────────────────────
        tbl = Table(title="Channel offsets", header_style="bold cyan")
        tbl.add_column("CH", justify="right")
        tbl.add_column("Offset", justify="right")
        tbl.add_column("Gain",   justify="right")

        for ch in indices:
            resp = dev.command(f"RD OFFSET CH {ch}")
            m = _OFFSET_PAT.search(resp)
            if m:
                off, g = m.groups()
                tbl.add_row(f"{ch:02}", off, g)
            else:
                tbl.add_row(f"{ch:02}", "err", "err")
        console.print(tbl)

        # ── AFE register tables ─────────────────────────────────────────
        for afe in range(5):
            reg_table = Table(
                title=f"AFE{afe} registers", header_style="bold cyan"
            )
            reg_table.add_column("Reg", width=6)
            reg_table.add_column("Raw", width=8, style="magenta")
            reg_table.add_column("Field", width=18, style="yellow")
            reg_table.add_column("Meaning")

            # SPI registers 0x04, 0x33, 0x34
            for reg in (4, 51, 52):
                resp = dev.command(f"RD AFE {afe} REG {reg}")
                m = _REG_PAT.search(resp)
                if not m:
                    reg_table.add_row(f"{reg:#04x}", "err", "", "<parse error>")
                    continue

                value = int(m.group(2), 0)
                spi_addr = _SPI_MAP[reg]

                first = True
                for line in pretty_print.__self__.decode(spi_addr, value):
                    field, meaning = line.split("= ")
                    field, meaning = field.strip(), meaning.strip()
                    if first:
                        reg_table.add_row(f"{reg:#04x}", f"0x{value:04X}", field, meaning)
                        first = False
                    else:
                        reg_table.add_row("", "", field, meaning)

            # VGAIN
            resp = dev.command(f"RD AFE {afe} VGAIN")
            m = _VGAIN_PAT.search(resp)
            if m:
                vreg, vgain = m.groups()
                reg_table.add_row("VGAIN", f"0x{int(vreg):04X}", "DAC_REG", f"{vreg}  GAIN={vgain}")
            else:
                reg_table.add_row("VGAIN", "err", "", "<parse error>")

            console.print(reg_table)

        dev.close()
