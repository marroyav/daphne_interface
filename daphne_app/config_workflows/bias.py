# daphne_app/config_workflows/bias.py
"""
Bias-DAC and TRIM helpers
========================

• configure_bias()  – write the same VBIAS value to all AFEs
• configure_trim()  – write per-channel TRIM DACs
• check_bias()      – read back VBIASx / POWER / TEMP and print a Rich table
• check_trim()      – dump CH00…CH39 TRIM registers (5 × 8 grid)
"""

from __future__ import annotations

from typing import Dict, List
import re

import rich
from rich.table import Table
from rich.console import Console
from rich import box

from daphne_app.hardware.daphne import Daphne
from daphne_app.utils.ip_utils     import endpoint_ip

# ──────────────────────────────── helpers ─────────────────────────────────
# ---- TRIM value regex ----------------------------------------------------
_TRIM_RE = re.compile(
    r"""(?:TRIM\s+DAC\s+REG|TRIM\s+REG|VALUE)\s*=\s*(\d{1,4})""",
    re.IGNORECASE | re.VERBOSE,
)

def _parse_trim_value(resp: str) -> int | None:
    m = _TRIM_RE.search(resp)
    return int(m.group(1)) if m else None


# ---- Bias read-back regex ------------------------------------------------
_VAR_RE = re.compile(
    r"(VBIAS[0-4]|POWER\([^)]+\)|TEMP\([^)]+\))\s*=\s*([-+]?\d*\.?\d+)"
)

_EXPECTED_ORDER = [
    "VBIAS0",
    "VBIAS1",
    "VBIAS2",
    "VBIAS3",
    "VBIAS4",
]  # rest is appended in natural order


def _unit_of(var: str) -> str:
    if var.startswith("VBIAS"):
        return "mV"
    if var.startswith("POWER"):
        return "mA"
    if var.startswith("TEMP"):
        return "°C"
    return ""


# ╭────────────────────────────────────────────────────────────────────────╮
# │  CONFIGURE                                                             │
# ╰────────────────────────────────────────────────────────────────────────╯
def configure_bias(endpoints: List[int], *, vbias_mv: int = 0) -> None:
    """
    Write *vbias_mv* mV into **VBIASCTRL** on every selected board.
    """
    for suf in endpoints:
        ip  = endpoint_ip(suf)
        rich.print(f"[bold]→ set VBIASCTRL {vbias_mv} mV on {ip}[/]")
        dev = Daphne(ip)
        dev.command(f"WR VBIASCTRL V {vbias_mv}")
        dev.close()


def configure_trim(endpoints: List[int], *, trim_map: Dict[int, int]) -> None:
    """
    Write TRIM-DACs; *trim_map* keys are **global** channels 0-39.
    """
    for suf in endpoints:
        ip  = endpoint_ip(suf)
        rich.print(f"[bold]→ write TRIM map on {ip}[/]")
        dev = Daphne(ip)
        for ch, val in trim_map.items():
            dev.command(f"WR TRIM CH {ch} V {val}")
        dev.close()


# ╭────────────────────────────────────────────────────────────────────────╮
# │  CHECK                                                                 │
# ╰────────────────────────────────────────────────────────────────────────╯
def check_bias(endpoints: List[int]) -> None:
    """
    Pretty Rich table with VBIAS0-4, POWER(…), TEMP(…) values.
    """
    cons = Console()

    for suf in endpoints:
        ip  = endpoint_ip(suf)
        dev = Daphne(ip)
        rsp = dev.command("RD VM ALL")
        dev.close()

        vars = {k: float(v) for k, v in _VAR_RE.findall(rsp)}

        cons.rule(f"[bold blue]Bias read-back {ip}")

        table = Table(box=box.MINIMAL_DOUBLE_HEAD)
        table.add_column("Variable", style="cyan")
        table.add_column("Value",   justify="right")
        table.add_column("Unit",    justify="center")

        # order: VBIAS0…4 first, then everything else
        ordered_keys = _EXPECTED_ORDER + [k for k in vars if k not in _EXPECTED_ORDER]

        for key in ordered_keys:
            val  = vars.get(key, None)
            unit = _unit_of(key)

            if val is None:
                table.add_row(key, "—", unit, style="dim")
            else:
                style = ""
                if key.startswith("TEMP") and val > 55:
                    style = "bold red"
                table.add_row(key, f"{val:,.1f}", unit, style=style)

        cons.print(table)


def check_trim(endpoints: List[int]) -> None:
    """
    Dump TRIM DAC registers (0-4095) in eight-channel rows.
    """
    for suf in endpoints:
        ip  = endpoint_ip(suf)
        rich.print(f"[bold]→ TRIM read-back {ip}[/]")

        dev = Daphne(ip)

        row: List[str] = []
        for ch in range(40):
            val = _parse_trim_value(dev.command(f"RD TRIM CH {ch}"))
            row.append(f"{val:02}" if val is not None else "--")
            if ch % 8 == 7:
                start = ch - 7
                rich.print(f"  CH{start:02d}-{ch:02d}: {' '.join(row)}")
                row.clear()

        dev.close()
