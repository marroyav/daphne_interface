"""
Configure and/or verify the DAPHNE self-trigger path (match-filter logic).

Registers touched
-----------------
  * 0x6001  – channel enable mask (for data mode; written elsewhere)
  * 0x6002  – Self-trigger Module configuration
  * 0x6003  – per-AFE compensator enable
  * 0x6004  – per-AFE digital inverter enable
  * 0x6010  – ad-hoc trigger value
  * 0x6100  – cross-correlation / discrimination thresholds
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from daphne_app.hardware.daphne import Daphne
from rich.console import Console
from rich.table import Table
from tqdm import tqdm

from daphne_app.utils.ip_utils import endpoint_ip


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────


def _fmt_mask40(mask: int) -> str:
    """Pretty-print a 40-bit channel mask as ‘xxxxxxxx xx xxxxxxxx …’."""
    bits = f"{mask:040b}"
    groups = [bits[i : i + 8] for i in range(0, 40, 8)]
    return " ".join(groups)


# ----------------------------------------------------------------------
# Translate keys coming from the JSON file so they match the kwargs
# that self_trigger.configure() expects.
# ----------------------------------------------------------------------


def _translate_json_kwargs(kw: dict[str, Any]) -> dict[str, Any]:
    """
    Convert JSON field names (sometimes with dashes) into the parameter
    names that `self_trigger.configure()` takes.
    Unrecognised items are left untouched so errors surface early.
    """
    new: dict[str, Any] = {}

    # helper -----------------------------------------------------------
    def pop_many(*names: str) -> None:
        for n in names:
            if n in kw:
                new[n] = kw.pop(n)

    # 1. 1-to-1 simple fields -----------------------------------------
    pop_many(
        "mask_enable",
        "module_cfg",
        "comp_enable",
        "inv_enable",
        "adhoc_cmd",
        "xc_thresh",
        "pedestal_length",
        "slope_mode",
        "slope_threshold",
        "filter_mode",
        "spybuffer_channel",
    )

    # 2. allow legacy “threshold” (maps onto mask_enable)
    if "threshold" in kw:
        new["mask_enable"] = kw.pop("threshold")

    # 3. tolerate JSON keys with dashes -------------------------------
    for k in list(kw):
        if "-" in k:
            kw[k.replace("-", "_")] = kw.pop(k)

    # 4. nested x-corr thresholds (42-bit register) -------------------
    if "self_trigger_xcorr" in kw:
        xcorr = kw.pop("self_trigger_xcorr")
        corr  = xcorr.get("correlation_threshold", 300)     # 28 LSB
        discr = xcorr.get("discrimination_threshold", -80)  # 14 MSB (signed)
        new["xc_thresh"] = (corr & 0x0FFFFFFF) | ((discr & 0x3FFF) << 28)

    # 5. channel-lists → bit-masks ------------------------------------
    def _bitmask(ch_list):
        mask = 0
        for ch in ch_list:
            mask |= 1 << int(ch)
        return mask

    if "enable_compensator" in kw:
        new["comp_enable"] = _bitmask(kw.pop("enable_compensator"))

    if "enable_inverter" in kw:
        new["inv_enable"] = _bitmask(kw.pop("enable_inverter"))

    # 6. pass through anything else -----------------------------------
    new.update(kw)
    return new
# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def configure(  # noqa: C901  – keep public signature unfolded for clarity
    ips: Sequence[int],
    progress: bool | str = "auto",
    # individual register fields (all optional)
    mask_enable: int | None = None,
    module_cfg: int | None = None,
    comp_enable: int | None = None,
    inv_enable: int | None = None,
    adhoc_cmd: int | None = None,
    xc_thresh: int | None = None,
    # “convenience” fields (translated into module_cfg bits)
    filter_mode: str | None = None,  # "inverted", "raw", …
    slope_mode: str | None = None,   # "16", "20"
    slope_threshold: int | None = None,
    pedestal_length: int | None = None,
    spybuffer_channel: int | None = None,
    *,
    extra_cfg: dict[str, int] | None = None,
) -> None:
    """
    Configure the match-filter (“self-trigger”) path for each endpoint in *ips*.

    Pass either raw register words or the higher-level convenience fields;
    the latter take precedence.
    """
    con = Console()

    for suffix in ips:
        full_ip = endpoint_ip(suffix)
        dev = Daphne(full_ip)

        # ── decide progress-bar use ───────────────────────────────────────
        use_tqdm = (
            progress
            if isinstance(progress, bool)
            else getattr(dev, "_is_tty", getattr(dev, "_tty", False))
        )
        pbar = tqdm(total=1, disable=not use_tqdm,
                    desc=f"Self-trigger {full_ip}", unit="cfg")

        # ── write individual registers ───────────────────────────────────
        if mask_enable is not None:
            dev.command(f"WR 0x6001 {mask_enable:#x}")    # 40-bit mask

        # build 0x6002 from either raw word or convenience fields
        if module_cfg is None:
            module_cfg = 0
            if filter_mode is not None:
                selector = {
                    "compensated": 0b00,
                    "inverted":    0b01,
                    "correlated":  0b10,
                    "raw":         0b11,
                }[filter_mode]
                module_cfg |= selector
            if slope_mode is not None:
                module_cfg |= (0 if slope_mode == "16" else 1) << 8
            if slope_threshold is not None:
                module_cfg |= (slope_threshold & 0x7F) << 9
            if pedestal_length is not None:
                module_cfg |= ((pedestal_length // 8) & 0x1F) << 16
            if spybuffer_channel is not None:
                module_cfg |= (spybuffer_channel & 0x3F) << 21

        dev.command(f"WR 0x6002 {module_cfg:#x}")

        if comp_enable is not None:
            dev.command(f"WR 0x6003 {comp_enable:#x}")

        if inv_enable is not None:
            dev.command(f"WR 0x6004 {inv_enable:#x}")

        if adhoc_cmd is not None:
            dev.command(f"WR 0x6010 {adhoc_cmd:#x}")

        if xc_thresh is not None:
            dev.command(f"WR 0x6100 {xc_thresh:#x}")

        # extra arbitrary registers (useful for debugging)
        if extra_cfg:
            for addr, val in extra_cfg.items():
                dev.command(f"WR {addr:#x} {val:#x}")

        pbar.update(1)
        pbar.close()

        # ── pretty print summary ──────────────────────────────────────────
        table = Table(title=f"Self-trigger settings @ {full_ip}", show_header=True,
                      header_style="bold magenta")
        table.add_column("Register")
        table.add_column("Value")
        table.add_column("Meaning / decoded")

        table.add_row("0x6001", f"{mask_enable:#x}" if mask_enable is not None else "—",
                      _fmt_mask40(mask_enable) if mask_enable is not None else "")
        table.add_row("0x6002", f"{module_cfg:#x}",
                      f"selector={module_cfg & 0x3:02b}, "
                      f"slope_thr={(module_cfg >> 9) & 0x7F}, "
                      f"ped_len={(module_cfg >> 16) & 0x1F}×8")
        table.add_row("0x6003", f"{comp_enable:#x}" if comp_enable is not None else "—",
                      "compensator enable mask")
        table.add_row("0x6004", f"{inv_enable:#x}" if inv_enable is not None else "—",
                      "inverter enable mask")
        table.add_row("0x6010", f"{adhoc_cmd:#x}" if adhoc_cmd is not None else "—",
                      "ad-hoc trigger value")
        table.add_row("0x6100", f"{xc_thresh:#x}" if xc_thresh is not None else "—",
                      "corr / discr thresholds")

        con.print(table)


# ----------------------------------------------------------------------
# Back-compat shim for the check CLI
# ----------------------------------------------------------------------
def check(ips, *args, **kwargs):
    """
    Historical name kept so that `daphne check self-trigger …` continues
    to work.  It simply forwards to :pyfunc:`configure`.
    """
    return configure(ips, *args, **kwargs)
