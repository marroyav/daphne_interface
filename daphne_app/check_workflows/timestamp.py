from __future__ import annotations
"""
Timestamp check – prints consecutive TS values in a Rich panel.

Green border  → timestamps are consecutive and non-zero
Yellow border → any 0 or non-consecutive value
Red border    → read failure
"""

from typing import Sequence
from rich.panel import Panel
from rich.console import Console
from rich.text import Text
from daphne_app.utils.ip_utils import endpoint_ip
from ..hardware.daphne import Daphne

console = Console()
__all__ = ["check"]


def _analyse(ts: list[int]) -> tuple[str, str]:
    """Return (status, message)."""
    if any(t == 0 for t in ts):
        return "yellow", "⚠ Contains 0"
    if all(ts[i + 1] - ts[i] == 1 for i in range(len(ts) - 1)):
        return "green", "✓ Consecutive"
    return "yellow", "⚠ Non-consecutive"


def check(ips: Sequence[int]) -> None:                          # noqa: D401
    for suffix in ips:
        full_ip = endpoint_ip(suffix)
        try:
            dev = Daphne(full_ip)
            dev.write_reg(0x2000, [1234])          # trigger spy buffers
            ts_raw = dev.read_reg(0x40500000, 4)[2:]
            dev.close()

            colour, note = _analyse(ts_raw)
            body = Text(f"Timestamps:\n{ts_raw}\n{note}")
            panel = Panel(body, title=full_ip, border_style=colour)
            console.print(panel)

        except Exception as exc:                                    # noqa: BLE001
            panel = Panel(f"Error: {exc}", title=full_ip,
                          border_style="red")
            console.print(panel)
