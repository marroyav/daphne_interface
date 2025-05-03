# daphne_app/config_workflows/bias.py
"""
Bias-DAC helpers
================

• configure_bias()  – write one VBIASCTRL value to the board
• configure_trim()  – write per-channel TRIM DACs
• check_bias()      – merged table: VBIAS, POWER/TEMP  +  BIASSET DACs
• check_trim()      – grid dump of the 40 TRIM DAC registers
"""

from __future__ import annotations

import re
from typing import Dict, List

import rich
from rich.table import Table
from rich.console import Console
from rich import box

from daphne_app.hardware.daphne import Daphne
from daphne_app.utils.ip_utils import endpoint_ip

# ────────────────────────── regex helpers ────────────────────────────
_TRIM_RE = re.compile(
    r"(?:TRIM\s+DAC\s+REG|TRIM\s+REG|VALUE)\s*=\s*(\d{1,4})",
    flags=re.I,
)
_VAR_RE = re.compile(
    r"(VBIAS[0-4]|POWER\([-+0-9.a-zA-Z]+\)|TEMP\([^)]+\))"
    r"\s*=\s*([-+]?\d*\.?\d+)"
)
_BIASSET_RE = re.compile(r"BIASSET\s+DAC\s+REG=\s*(\d+)", flags=re.I)

_EXPECTED_ORDER = [f"VBIAS{i}" for i in range(5)]  # show 0-4 first


def _unit_of(var: str) -> str:
    if var.startswith("VBIAS"):
        return "mV"
    if var.startswith("POWER"):
        return "mA"
    if var.startswith("TEMP"):
        return "°C"
    return ""


# ╭────────────────────────────────────────────────────────────────────╮
# │ CONFIGURE                                                          │
# ╰────────────────────────────────────────────────────────────────────╯
def configure_bias(endpoints: List[int], *, vbias_mv: int = 0) -> None:
    """Write *vbias_mv* into VBIASCTRL on every selected board."""
    for suf in endpoints:
        ip = endpoint_ip(suf)
        rich.print(f"[bold]→ VBIASCTRL {vbias_mv} mV  @ {ip}[/]")
        dev = Daphne(ip)
        dev.command(f"WR VBIASCTRL V {vbias_mv}")
        dev.close()


def configure_bias(
    endpoints: list[int],
    *,
    vbias_mv: int = 0,
    bias_set: list[int] | None = None,   # ← new
) -> None:
    """
    • Write *VBIASCTRL* once per board
    • If *bias_set* is given (5 ints), write BIASSET AFE0…4
    """
    for suf in endpoints:
        ip  = endpoint_ip(suf)
        rich.print(f"[bold]→ VBIASCTRL {vbias_mv} mV  @ {ip}[/]")
        dev = Daphne(ip)
        dev.command(f"WR VBIASCTRL V {vbias_mv}")

        if bias_set:
            for afe, dac in enumerate(bias_set):
                dev.command(f"WR BIASSET AFE {afe} V {dac}")

        dev.close()

# ╭────────────────────────────────────────────────────────────────────╮
# │ CHECK – Bias / Power / Temp / DACs                                 │
# ╰────────────────────────────────────────────────────────────────────╯
# ── still in daphne_app/config_workflows/bias.py ────────────────────
def check_bias(endpoints: list[int]) -> None:
    """
    Pretty Rich table with VBIAS0-4, POWER/TEMP **and** BIASSET DACs.
    """
    cons = Console()

    for suf in endpoints:
        ip = endpoint_ip(suf)
        dev = Daphne(ip)

        # --- VM ALL ------------------------------------------------------
        rsp = dev.command("RD VM ALL")
        vars = {k: float(v) for k, v in _VAR_RE.findall(rsp)}

        # --- BIASSET read-back ------------------------------------------
        biasset: list[str] = []
        for afe in range(5):
            try:
                txt = dev.command(f"RD BIASSET AFE {afe}")
                m   = re.search(r"BIASSET DAC REG=\s*(\d+)", txt)
                biasset.append(m.group(1) if m else "—")
            except Exception:
                biasset.append("—")

        dev.close()

        # --- VBIAS + POWER/TEMP table -----------------------------------
        cons.rule(f"[bold blue]Bias read-back {ip}")
        table = Table()
        table.add_column("Variable")
        table.add_column("Value", justify="right")
        table.add_column("Unit",  justify="center")

        ordered = _EXPECTED_ORDER + [k for k in vars if k not in _EXPECTED_ORDER]
        for key in ordered:
            val  = vars.get(key, None)
            unit = _unit_of(key)
            table.add_row(key, f"{val:.1f}" if val is not None else "—", unit)
        cons.print(table)

        # --- BIASSET table ----------------------------------------------
        bs_tbl = Table(title="BIASSET DACs")
        bs_tbl.add_column("AFE", justify="right")
        bs_tbl.add_column("DAC", justify="right")
        for afe, dac in enumerate(biasset):
            bs_tbl.add_row(str(afe), dac)
        cons.print(bs_tbl)

# ╭────────────────────────────────────────────────────────────────────╮
# │ CHECK – TRIM grid                                                  │
# ╰────────────────────────────────────────────────────────────────────╯
def _parse_trim_value(resp: str) -> int | None:
    m = _TRIM_RE.search(resp)
    return int(m.group(1)) if m else None


def check_trim(endpoints: List[int]) -> None:
    """Dump the 40 TRIM DAC registers in eight-channel rows."""
    for suf in endpoints:
        ip = endpoint_ip(suf)
        rich.print(f"[bold]→ TRIM read-back {ip}[/]")

        dev = Daphne(ip)
        row: List[str] = []

        for ch in range(40):
            val = _parse_trim_value(dev.command(f"RD TRIM CH {ch}"))
            row.append(f"{val:04}" if val is not None else "--")
            if ch % 8 == 7:
                start = ch - 7
                rich.print(f"  CH{start:02d}-{ch:02d}: {' '.join(row)}")
                row.clear()

        dev.close()
