# daphne_app/config_workflows/bias.py
"""
Bias-DAC and TRIM utilities
===========================

• configure_bias()     – write the same bias setting to all AFEs
• configure_trim()     – write per-channel TRIM values
• check_bias()         – read back VBIASx, POWER, TEMP
• check_trim()         – dump CH00…CH39 TRIM registers in a nice table
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Dict
import json
import re
import rich

from daphne_app.hardware.daphne import Daphne
from daphne_app.utils.ip_utils import endpoint_ip, ip_suffix

# ──────────────────────────────────────────────────────────────────────────
# helpers – common regex & parser
# ──────────────────────────────────────────────────────────────────────────
# All known firmware strings for TRIM read-back:
#
#   “… TRIM DAC REG=
#    0DAC GAIN=0 …”
#   “… TRIM REG= 123  …”
#   “… VALUE=4095 …”
#
TRIM_VALUE_RE = re.compile(
    r"""
    (?:TRIM\s+DAC\s+REG|TRIM\s+REG|VALUE)\s*=\s*   # any prefix, ignore case
    (\d{1,4})                                      # decimal number (0–4095)
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _parse_trim_value(resp: str) -> int | None:
    """Return the integer value (0-4095) or *None* if parsing fails."""
    m = TRIM_VALUE_RE.search(resp)
    return int(m.group(1)) if m else None


# ╭──────────────────────────────────────────────────────────────────────╮
# │  CONFIGURE – bias & trim                                            │
# ╰──────────────────────────────────────────────────────────────────────╯
def configure_bias(endpoints: List[int], *, vbias_mv: int = 0) -> None:
    """
    Write the same VBIASCTRL value (mV) to every listed endpoint.
    """
    for suf in endpoints:
        ip = endpoint_ip(suf)
        rich.print(f"[bold]→ set VBIASCTRL {vbias_mv} mV on {ip}[/]")
        dev = Daphne(ip)
        dev.command(f"WR VBIASCTRL V {vbias_mv}")
        dev.close()


def configure_trim(
    endpoints: List[int],
    *,
    trim_map: Dict[int, int],   # {global_ch: trim_dac}
) -> None:
    """
    Write per-channel TRIM DACs.

    *trim_map* keys are **global** channel numbers (0-39).
    """
    for suf in endpoints:
        ip = endpoint_ip(suf)
        rich.print(f"[bold]→ write TRIM map on {ip}[/]")
        dev = Daphne(ip)

        for ch, val in trim_map.items():
            dev.command(f"WR TRIM CH {ch} V {val}")

        dev.close()


# ╭──────────────────────────────────────────────────────────────────────╮
# │  CHECK – bias & trim                                                │
# ╰──────────────────────────────────────────────────────────────────────╯
def check_bias(endpoints: List[int]) -> None:
    """
    Print VBIAS0…4, POWER, TEMP for every endpoint.
    """
    for suf in endpoints:
        ip = endpoint_ip(suf)
        rich.print(f"[bold]→ bias read-back {ip}[/]")
        dev = Daphne(ip)
        info = dev.read_bias()         # util already returns a dict
        rich.print(info)
        dev.close()


def check_trim(endpoints: List[int]) -> None:
    """
    Dump TRIM DAC register of every channel in a 5×8 grid.
    """
    for suf in endpoints:
        ip = endpoint_ip(suf)
        rich.print(f"[bold]→ TRIM read-back {ip}[/]")

        dev = Daphne(ip)

        line: List[str] = []
        for ch in range(40):
            rsp = dev.command(f"RD TRIM CH {ch}")
            val = _parse_trim_value(rsp)

            line.append(f"{val:02}" if val is not None else "--")

            if ch % 8 == 7:            # print every 8 channels
                start = ch - 7
                rich.print(f"  CH{start:02d}-{ch:02d}: {' '.join(line)}")
                line.clear()

        dev.close()
