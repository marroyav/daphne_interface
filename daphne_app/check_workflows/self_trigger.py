# daphne_app/check_workflows/self_trigger.py
"""
Self-trigger register dump & decode.

Run
    daphne check self-trigger --ip 7,9
"""

from __future__ import annotations
from typing import List

import rich
from rich.table import Table

from daphne_app.hardware.daphne import Daphne
from daphne_app.utils.ip_utils import endpoint_ip

# ────────────────────────── addresses ──────────────────────────
REG_6001 = 0x6001  # sender input-enable mask      (40 bit)
REG_6002 = 0x6002  # module configuration          (32 bit)
REG_6003 = 0x6003  # compensator enable mask       (40 bit)
REG_6004 = 0x6004  # digital-inverter enable mask  (40 bit)
REG_6010 = 0x6010  # ad-hoc trigger value           (8 bit)
REG_6100 = 0x6100  # corr./discr. thresholds       (42 bit)

REG_LIST = [REG_6001, REG_6002, REG_6003, REG_6004, REG_6010, REG_6100]


# ────────────────────────── raw read ───────────────────────────
def _rd(dev: Daphne, addr: int) -> int | None:
    try:
        return dev.read_reg(addr, 1)[2]
    except Exception:
        return None


# ─────────────────────── mask helpers ──────────────────────────
def _channels_from_mask(mask: int | None) -> str:
    if mask is None:
        return ""
    ch = [str(i) for i in range(40) if (mask >> i) & 1]
    return ", ".join(ch) if ch else "—"


def _mask_str(mask: int | None) -> str:
    return f"0x{mask:010x}" if mask is not None else "—"


# ─────────────────────── decoders ──────────────────────────────
def _decode_6002(v: int | None) -> str:
    if v is None:
        return ""
    selector = v & 0x3
    sel_str  = {
        0b00: "compensated (deprecated)",
        0b01: "comp+inv",
        0b10: "xcorr",
        0b11: "raw",
    }[selector]
    slope_mode = "20-sample" if (v >> 8) & 1 else "16-sample"
    slope_thr  = (v >> 9)  & 0x7F
    ped_len    = ((v >> 16) & 0x1F) * 8
    spy_sel    = (v >> 21) & 0x3F
    return (
        f"selector={sel_str}  "
        f"slope_mode={slope_mode}  "
        f"slope_thr={slope_thr}  "
        f"ped_len={ped_len}  "
        f"spybuffer_ch={spy_sel}"
    )


def _decode_6010(v: int | None) -> str:
    return str(v) if v is not None else ""


def _decode_6100(v: int | None) -> str:
    if v is None:
        return ""
    corr   =  v & 0x0FFFFFFF                   # 28 LSB
    discr  = (v >> 28) & 0x3FFF                # signed 14 MSB
    if discr & 0x2000:                         # sign-extend
        discr -= 0x4000
    return f"corr_thr={corr}  discr_thr={discr}"


DECODER = {
    REG_6001: lambda v: f"enabled ch → {_channels_from_mask(v)}",
    REG_6002: _decode_6002,
    REG_6003: lambda v: f"compensator on ch → {_channels_from_mask(v)}",
    REG_6004: lambda v: f"inverter on ch → {_channels_from_mask(v)}",
    REG_6010: _decode_6010,
    REG_6100: _decode_6100,
}


# ───────────────────── pretty printer ──────────────────────────
def _pretty(ip: str, values: dict[int, int | None]) -> None:
    t = Table(
        title=f"Self-trigger registers – {ip}",
        header_style="bold cyan",
        show_header=True,
    )
    t.add_column("Register", justify="right")
    t.add_column("Raw value", justify="right")
    t.add_column("Decoded meaning / fields", justify="left")

    for a in REG_LIST:
        val  = values[a]
        raw  = _mask_str(val) if a in (REG_6001, REG_6003, REG_6004) else (
               f"0x{val:x}" if val is not None else "—")
        dec  = DECODER[a](val)
        t.add_row(f"0x{a:04x}", raw, dec)

    rich.print(t)


# ───────────────────────── public API ──────────────────────────
def check(ips: List[int]) -> None:
    """Dump & decode self-trigger registers for each endpoint suffix."""
    for suf in ips:
        dev = Daphne(endpoint_ip(suf))
        try:
            regs = {addr: _rd(dev, addr) for addr in REG_LIST}
            _pretty(endpoint_ip(suf), regs)
        finally:
            dev.close()
