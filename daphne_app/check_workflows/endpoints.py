from __future__ import annotations
"""
Timing-endpoint & clock health check (Rich-table version)

* Shows firmware rev
* Displays every MMCM/LOS bit with colour OK/WARN
* Decodes the FSM state into a line of text
"""

from typing import Sequence
from rich.table import Table
from rich.console import Console
from rich.panel import Panel

from ..hardware.daphne import Daphne
from ..utils.colors import RED, YELLOW, GREEN, RESET

console = Console()
__all__ = ["verify"]

# FSM decode (same mapping as original script)
_STATE_MSG = {
    0:  "Starting state after reset",
    1:  "Waiting for SFP LOS to go low",
    2:  "Waiting for good frequency check",
    3:  "Waiting for phase adjustment",
    4:  "Waiting for comma alignment",
    5:  "Waiting for 8b10 good packet",
    6:  "Waiting for phase-adj command",
    7:  "Waiting for timestamp init",
    8:  "Good to go!!!",
    12: "Error in RX",
    13: "Error in timestamp check",
    14: "Physical-layer error",
}

def _status(ok: bool) -> str:
    """Colour-coded YES/NO."""
    return f"[green]OK[/]" if ok else f"[yellow]WARN[/]"

def verify(ips: Sequence[int]) -> None:                       # noqa: D401
    console.print(
        Panel("[bold magenta]Expecting: same FW & 'Good to go!!!'[/]",
              expand=False))

    for suffix in ips:
        full_ip = f"10.73.137.{100 + suffix}"

        try:
            dev = Daphne(full_ip)
            fw     = dev.read_reg(0x9000, 1)[2]
            epstat = dev.read_reg(0x4000, 1)[2]
            dev.close()

            # Build Rich table
            tbl = Table(title=f"Endpoint {full_ip}",
                        header_style="bold cyan")
            tbl.add_column("Check")
            tbl.add_column("Status", justify="right")

            tbl.add_row("Firmware", f"0x{fw:08X}")
            tbl.add_row("MMCM0 LOCKED",          _status(bool(epstat & 0x1)))
            tbl.add_row("MMCM1 LOCKED",          _status(bool(epstat & 0x2)))
            tbl.add_row("CDR signal OK",         _status(not (epstat & 0x10)))
            tbl.add_row("CDR LOCKED",            _status(not (epstat & 0x20)))
            tbl.add_row("Timing SFP LOS=0",      _status(not (epstat & 0x40)))
            tbl.add_row("Timing SFP present",    _status(not (epstat & 0x80)))
            tbl.add_row("Timestamp valid",       _status(bool(epstat & 0x1000)))

            state = (epstat >> 8) & 0xF
            msg = _STATE_MSG.get(state, f"Unknown ({state})")
            colour = "green" if state == 8 else "yellow"
            tbl.add_row("FSM state", f"[{colour}]{msg}[/{colour}]")

            console.print(tbl)

        except Exception as exc:                                    # noqa: BLE001
            console.print(f"[{RED}]Error talking to {full_ip}: {exc}[/]")
