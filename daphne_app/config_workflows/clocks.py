"""
Clock- and timing-interface configuration workflow.

This module is called by the Typer CLI:

    daphne clocks-only --ip 4,5
"""

from __future__ import annotations

import time
from typing import Iterable, Sequence

from ..hardware.daphne import Daphne
from ..utils.colors import GREEN, RED, YELLOW, RESET


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _endpoint_ip(suffix: int) -> str:
    """Convert the last octet to the full 10.73.137.* address."""
    return f"10.73.137.{100 + suffix}"


def _sleep() -> None:
    """Short, readable delay used after hardware resets."""
    time.sleep(0.5)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def configure(ips: Sequence[int], *, use_endpoint: int = 0) -> None:
    """
    Configure the timing endpoint / master clock on each selected board.

    Parameters
    ----------
    ips
        Iterable of endpoint suffixes (e.g. [4, 5, 7]).
    use_endpoint
        Value written to register 0x4001 to select timing source
        (0 = local master clock, 1 = timing endpoint lock, etc.).
    """
    for suffix in ips:
        full_ip = _endpoint_ip(suffix)
        print(f"\nConfiguring endpoint {full_ip}")

        try:
            dev = Daphne(full_ip)

            # ------------------------------------------------------------------
            # 1.  Identify board / firmware
            # ------------------------------------------------------------------
            fw = dev.read_reg(0x9000, 1)[2]
            print(f"DAPHNE firmware version: {GREEN}{fw:08X}{RESET}")

            # ------------------------------------------------------------------
            # 2.  Main clock / timing reset sequence
            # ------------------------------------------------------------------
            dev.write_reg(0x4001, [use_endpoint])   # select timing source
            dev.write_reg(0x4003, [1234])           # reset timing endpoint
            _sleep()
            dev.write_reg(0x4002, [1234])           # reset master-clock MMCM1
            _sleep()
            dev.write_reg(0x2001, [1234])           # AFE automatic alignment
            _sleep()

            # ------------------------------------------------------------------
            # 3.  Read-back checks
            # ------------------------------------------------------------------
            align_done = dev.read_reg(0x2002, 1)[2]
            mclk_state = dev.read_reg(0x4000, 1)[2]
            print(f"Alignment status (should be 0x1F): {GREEN}{align_done:02X}{RESET}")
            print(f"MCLK state bits: {GREEN}{bin(mclk_state)[2:]}{RESET}")

            for afe in range(5):
                err = dev.read_reg(0x2010 + afe, 1)[2]
                colour = GREEN if err == 0 else RED
                print(f"AFE{afe} Error Count: {colour}{err:02X}{RESET}")

            dev.close()

        except Exception as exc:  # noqa: BLE001
            print(f"{RED}Error while configuring {full_ip}: {exc}{RESET}")
