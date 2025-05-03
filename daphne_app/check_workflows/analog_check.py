from __future__ import annotations
"""
Analog-chain reader – Rich tables, no progress bar.

• One table with OFFSET/gain for all 40 channels
• One decoded-register table for each AFE (0x04, 0x33, 0x34) + VGAIN
"""

from typing import Sequence
import re
from rich.table import Table
from rich.console import Console
from rich.panel import Panel

from ..hardware.daphne import Daphne
from ..utils.colors import RED, CYAN, RESET
from ..utils.register_decode import decode   # helper made earlier
from daphne_app.utils.ip_utils import endpoint_ip
console = Console()

__all__ = ["run"]

_offset_pat = re.compile(r"OFFSET DAC REG= (\d+).*DAC GAIN=(\d+)")
_reg_pat    = re.compile(r"REG\s*([0-9A-Fa-fx]+)\s*=\s*([0-9A-Fa-fx]+)")
_vgain_pat  = re.compile(r"VGAIN DAC REG= (\d+).*DAC GAIN=(\d+)")

_SPI_MAP = {4: 0x04, 51: 0x33, 52: 0x34}


# ---------------------------------------------------------------------
#  Main entry
# ---------------------------------------------------------------------
def run(ips: Sequence[int]) -> None:                       # noqa: D401
    for suffix in ips:
        full_ip = endpoint_ip(suffix)
        console.print(Panel(f"[bold]{full_ip}[/]", style="cyan"))

        try:
            dev = Daphne(full_ip)

            # ---------------------------------------------------------
            # Channel offset table
            # ---------------------------------------------------------
            ch_table = Table(title="Channel offsets", header_style="bold cyan")
            ch_table.add_column("CH",      justify="right")
            ch_table.add_column("Offset",  justify="right")
            ch_table.add_column("Gain",    justify="right")

            for ch in range(40):
                resp = dev.command(f"RD OFFSET CH {ch}")
                m = _offset_pat.search(resp)
                if m:
                    dac, gain = m.groups()
                    ch_table.add_row(f"{ch:02}", dac, gain)
                else:
                    ch_table.add_row(f"{ch:02}", "err", "err")

            console.print(ch_table)

            # ---------------------------------------------------------
            # AFE register tables
            # ---------------------------------------------------------
            for afe in range(5):
                reg_table = Table(
                    title=f"AFE{afe} registers",
                    header_style="bold cyan"
                )
                reg_table.add_column("Reg",   width=6)
                reg_table.add_column("Raw",   width=8, style="magenta")
                reg_table.add_column("Field", width=18, style="yellow")
                reg_table.add_column("Meaning")

                # SPI registers
                for reg in (4, 51, 52):
                    resp = dev.command(f"RD AFE {afe} REG {reg}")
                    m = _reg_pat.search(resp)
                    if not m:
                        reg_table.add_row(f"{reg:#04x}", "err", "", "<parse error>")
                        continue

                    value = int(m.group(2))
                    spi_addr = _SPI_MAP[reg]

                    first = True
                    for line in decode(spi_addr, value):
                        field, meaning = line.split("= ")
                        field, meaning = field.strip(), meaning.strip()
                        if first:
                            reg_table.add_row(f"{reg:#04x}", f"0x{value:04X}", field, meaning)
                            first = False
                        else:
                            reg_table.add_row("", "", field, meaning)

                # VGAIN
                resp = dev.command(f"RD AFE {afe} VGAIN")
                m = _vgain_pat.search(resp)
                if m:
                    vreg, vgain = m.groups()
                    reg_table.add_row("VGAIN", f"0x{int(vreg):04X}", "DAC_REG", f"{vreg}  GAIN={vgain}")
                else:
                    reg_table.add_row("VGAIN", "err", "", "<parse error>")

                console.print(reg_table)

            dev.close()

        except Exception as exc:                                 # noqa: BLE001
            console.print(f"[{RED}]Error talking to {full_ip}: {exc}[/{RED}]")


# End of file
