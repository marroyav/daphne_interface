from __future__ import annotations

"""
Decode and print the data-mode register (0x3001) for every selected
endpoint in a Rich table.

Dependencies:  rich
"""

from typing import Sequence
from rich.table import Table
from rich.console import Console

from ..hardware.daphne import Daphne
from ..utils.colors import RED
from ..utils.settings import data_mode   # YAML-driven expectations

console = Console()

__all__ = ["run"]


def _mode_name(byte_val: int) -> str:
    """Translate sender byte to a human-readable string."""
    if byte_val == 0xAA:
        return "full-streaming"
    if byte_val == 0x03:
        return "self-trigger"
    return f"0x{byte_val:02X} ?"


def run(ips: Sequence[int]) -> None:      # noqa: D401
    """Print a table with slot, raw 0x3001 value and mode name."""
    console.print("[bold]DAPHNE physical scheme – data-mode check[/bold]")

    table = Table(title="Data-mode register", header_style="bold cyan")
    table.add_column("IP",    style="bold")
    table.add_column("Slot",  justify="right")
    table.add_column("0x3001", style="magenta", justify="right")
    table.add_column("Mode")

    for suffix in ips:
        full_ip = f"10.73.137.{100 + suffix}"
        try:
            dev = Daphne(full_ip)

            slot   = (dev.read_reg(0x3000, 1)[2] >> 22) & 0xFF
            sender =  dev.read_reg(0x3001, 1)[2] & 0xFF
            mode_str = _mode_name(sender)

            table.add_row(full_ip, str(slot), f"0x{sender:02X}", mode_str)
            dev.close()

        except Exception as exc:           # noqa: BLE001
            msg = f"[{RED}]Error: {exc}[/]"
            table.add_row(full_ip, "-", "-", msg)

    console.print(table)
