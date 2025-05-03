from __future__ import annotations

"""Full‑stream trigger matrix configuration.

Directly ported from the legacy *conf_trigger.py* so that the CLI call
``daphne configure`` truly completes the full‑stream setup for endpoints
4, 5 and 7.

Public API
==========

``configure_full_stream(ips, *, configure=True)`` – write (or just read)
all relevant 0x5000‑series registers for each selected endpoint.

The register patterns still live in code; if you want to move them to
YAML later we can do so, but the critical thing was to get functional
parity with the original script.
"""

from typing import Sequence
from warnings import warn

from ..hardware.daphne import Daphne
from ..utils.colors import GREEN, YELLOW, RED, RESET
from ..utils.settings import is_full_stream
from daphne_app.utils.ip_utils import endpoint_ip

__all__ = ["configure_full_stream"]


# ------------------------------------------------------------------
# Convenience wrapper – returns the list defined in settings.yaml
# ------------------------------------------------------------------
def full_stream_endpoints() -> list[int]:
    """
    List of endpoint suffixes that should receive the trigger
    matrix when running in full-stream mode.
    """
    from daphne_app.utils.settings import settings
    return settings().get("full_stream_endpoints", [])


# ---------------------------------------------------------------------------
# Helper: generic read/write for one register
# ---------------------------------------------------------------------------

def _rw(dev: Daphne, address: int, value: int | None) -> None:  # noqa: D401
    if value is not None:
        dev.write_reg(address, [value])
    read_back = dev.read_reg(address, 1)[2]
    print(f"{hex(address)} = {read_back}")


# ---------------------------------------------------------------------------
# Endpoint‑specific register patterns (copied verbatim from old code)
# ---------------------------------------------------------------------------

def _process_endpoint_4(dev: Daphne, start_reg: int, configure: bool) -> None:
    reg = start_reg
    for k in range(2):
        for j in [0, 2, 5, 7, 1, 3, 4, 6]:
            value = 10 * k + j if configure else None
            _rw(dev, reg, value)
            reg += 1


def _process_endpoint_5(dev: Daphne, start_reg: int, configure: bool) -> None:
    reg = start_reg
    for k in [0]:
        for j in [0, 2, 5, 7, 1, 3, 4, 6]:
            value = 10 * k + j if configure else None
            _rw(dev, reg, value)
            reg += 1
    for k in [1]:
        for j in [0, 2, 5, 7]:
            value = 10 * k + j if configure else None
            _rw(dev, reg, value)
            reg += 1
    for k in [2]:
        for j in [1, 3, 4, 6]:
            value = 10 * k + j if configure else None
            _rw(dev, reg, value)
            reg += 1


def _process_endpoint_7(dev: Daphne, start_reg: int, configure: bool) -> None:
    reg = start_reg
    for k in [0, 1]:
        for j in [0, 2, 5, 7]:
            value = 10 * k + j if configure else None
            _rw(dev, reg, value)
            reg += 1
    for k in [2]:
        for j in range(8):
            value = 8 if configure else None  # original script wrote constant 8
            _rw(dev, reg, value)
            reg += 1


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def configure_full_stream(
    ips: Sequence[int], *, configure: bool = True
) -> None:  # noqa: D401
    """Configure or inspect the trigger matrix for each full‑stream board.

    Parameters
    ----------
    ips
        Endpoint suffixes to process.
    configure
        *True* (default) – write the register values then read‑back.
        *False* – **only** read the current contents.
    """

    for suffix in ips:
        if not is_full_stream(suffix):
            warn(
                f"{YELLOW}Endpoint {suffix} is not marked full‑stream; skipping.{RESET}",
                stacklevel=1,
            )
            continue

        full_ip = endpoint_ip(suffix)
        print(f"\n--- Trigger matrix for endpoint {full_ip} ---")

        try:
            dev = Daphne(full_ip)

            if suffix == 4:
                _process_endpoint_4(dev, 0x5000, configure)
            elif suffix == 5:
                _process_endpoint_5(dev, 0x5000, configure)
            elif suffix == 7:
                _process_endpoint_7(dev, 0x5000, configure)
            else:
                print(f"{YELLOW}No pattern defined for endpoint {suffix}{RESET}")

            dev.close()
        except Exception as exc:  # noqa: BLE001
            print(f"{RED}Error talking to {full_ip}: {exc}{RESET}")

