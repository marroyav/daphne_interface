from __future__ import annotations

"""
Configure the two data-mode registers (0x3000, 0x6001).

Typical use
-----------
>>> configure([7])                         # use value from settings.yaml
>>> configure([7], force_mode="self_trigger")
"""

from collections.abc import Iterable
from typing import Literal, Mapping

from daphne_app.hardware.daphne import Daphne
from rich.console import Console
from tqdm import tqdm

from daphne_app.utils.ip_utils import endpoint_ip
from daphne_app.utils.settings import settings, data_mode

console = Console()


# ──────────────────────────────────────────────────────────────────────
# helpers
# ──────────────────────────────────────────────────────────────────────
def _preset_from_settings(name: str) -> tuple[int, int] | None:
    """Return (reg_3000, reg_6001) if *name* exists in ``mode_presets``."""
    preset: Mapping[str, Mapping] | None = settings().get("mode_presets")
    if preset and name in preset:
        p = preset[name]
        return int(p["reg_3000"]), int(p["reg_6001"])
    return None


def _scan_data_modes(name: str) -> tuple[int, int] | None:
    """
    Fallback: find first endpoint in *data_modes* table whose
    ``mode`` field matches *name*.
    """
    for cfg in settings().get("data_modes", {}).values():
        if cfg["mode"] == name:
            return int(cfg["reg_3000"]), int(cfg["reg_6001"])
    return None


def _mode_to_regs(name: str | int) -> tuple[int, int]:
    """
    Resolve either a *mode name* **or** an *endpoint suffix* to
    ``(reg_3000, reg_6001)``.
    """
    name = name.replace("-", "_")

    if isinstance(name, int):
        cfg = data_mode(name)
        return int(cfg["reg_3000"]), int(cfg["reg_6001"])

    # name given → preset / scan
    regs = _preset_from_settings(name) or _scan_data_modes(name)
    if regs is None:
        raise KeyError(
            f"No register preset found for mode '{name}'. "
            "Add it under either 'mode_presets' or 'data_modes' "
            "in settings.yaml."
        )
    return regs


# ──────────────────────────────────────────────────────────────────────
# public API
# ──────────────────────────────────────────────────────────────────────
def configure(
    ips: Iterable[int],
    *,
    progress: bool | str = "auto",
    force_mode: Literal[
        "full_stream", "self_trigger", "hi_rate_self_trigger"
    ]
    | None = None,
) -> None:
    """
    Program registers 0x3000 / 0x6001 on every endpoint in *ips*.

    Parameters
    ----------
    ips
        List/iterable of endpoint suffixes (4 → 10.73.137.104, …).
    progress
        ``True`` | ``False`` | ``"auto"`` – show tqdm bar only if
        stdout is a TTY when set to ``"auto"``.
    force_mode
        Override the per-endpoint mode and write the given preset.
    """
    use_tqdm = (
        progress
        if isinstance(progress, bool)
        else __import__("sys").stdout.isatty()
    )
    ip_iter = tqdm(ips, desc="Data-mode", unit="endpoint") if use_tqdm else ips

    for suffix in ip_iter:
        full_ip = endpoint_ip(suffix)
        dev = Daphne(full_ip)

        mode = force_mode or data_mode(suffix)["mode"]
        reg_3000, reg_6001 = _mode_to_regs(mode)

        dev.command(f"WR 0x3000 {reg_3000:#x}")
        dev.command(f"WR 0x6001 {reg_6001:#x}")

        console.print(
            f"[cyan]{full_ip}[/] → "
            f"mode=[bold]{mode}[/] "
            f"(0x3000={reg_3000:#x}, 0x6001={reg_6001:#x})"
        )
