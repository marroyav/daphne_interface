from __future__ import annotations

"""
Trigger / FIFO / FLX counters – Rich-table version.
"""

from typing import Sequence
from rich.table import Table
from rich.console import Console

from ..hardware.daphne import Daphne
from ..utils.colors import RED
from daphne_app.utils.ip_utils import endpoint_ip
console = Console()
__all__ = ["spy"]


def spy(ips: Sequence[int]) -> None:                       # noqa: D401
    for suffix in ips:
        full_ip = endpoint_ip(suffix)
        try:
            dev = Daphne(full_ip)

            trigger = [dev.read_reg(0x40800000 + n * 0x8, 1)[2] for n in range(40)]
            fifo    = [dev.read_reg(0x40800140 + n * 0x8, 1)[2] for n in range(40)]
            flx     =  dev.read_reg(0x40800280, 1)[2]

            table = Table(title=f"Counters – {full_ip}",
                          header_style="bold cyan")
            table.add_column("CH",  justify="right")
            table.add_column("Trigger", style="green", justify="right")
            table.add_column("FIFO",    style="green", justify="right")
            table.add_column("FLX",     style="magenta", justify="right")

            for ch in range(40):
                table.add_row(
                    f"{ch:02}",
                    f"{trigger[ch]:010}",
                    f"{fifo[ch]:010}",
                    f"{flx:010}",
                )

            console.print(table)
            dev.close()

        except Exception as exc:                            # noqa: BLE001
            console.print(f"[{RED}]Error talking to {full_ip}: {exc}[/]")
