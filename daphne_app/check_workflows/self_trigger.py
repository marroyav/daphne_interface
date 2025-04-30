# daphne_app/check_workflows/self_trigger.py
"""
Self-trigger register dump & decode (0x600x page).

Run with
    daphne check self-trigger --ip 7,9
"""

from __future__ import annotations
from typing import List

import rich
from rich.table import Table

from daphne_app.hardware.daphne import Daphne
from daphne_app.utils.ip_utils import endpoint_ip

# ────────────────────────── constants ──────────────────────────
REG_6001 = 0x6001  # input-enable mask          (40 bits)
REG_6002 = 0x6002  # module configuration       (32 bits)
REG_6003 = 0x6003  # compensator enable mask    (40 bits)
REG_6004 = 0x6004  # inverter    enable mask    (40 bits)
REG_6010 = 0x6010  # ad-hoc trigger value        (8  bits)
REG_6100 = 0x6100  # corr. / discr. thresholds  (42 bits)

REG_LIST = [REG_6001, REG_6002, REG_6003, REG_6004, REG_6010, REG_6100]


# ────────────────────────── helpers ────────────────────────────
def _read(dev: Daphne, addr: int) -> int | None:
    """Return register value (Python int) or *None* on I/O error."""
    try:
        return dev.read_reg(addr, 1)[2]
    except Exception:
        return None


# ---------- decoders ------------------------------------------------------
def _decode_6002(val: int) -> str:
    if val is None:
        return ""
    sel   =  val        & 0x3
    slope = (val >> 8)  & 0x1
    thr   = (val >> 9)  & 0x7F
    ped   = (val >> 16) & 0x1F
    spy   = (val >> 21) & 0x3F
    msg = (
        f"selector={sel:02b}  "
        f"slope_mode={'20' if slope else '16'}  "
        f"slope_thr={thr:d}  "
        f"ped_len={ped*8}  "
        f"spy_ch={spy}"
    )
    return msg


def _decode_mask(val: int | None) -> str:
    return f"{val:010x}" if val is not None else ""   # 40-bit → 10 hex chars


def _decode_6010(val: int | None) -> str:
    return f"{val:d}" if val is not None else ""


def _decode_6100(val: int | None) -> str:
    if val is None:
        return ""
    corr =  val        & 0x0FFFFFFF          # 28 LSB
    discr = (val >> 28) & 0x3FFF             # 14 MSB
    # signed 14-bit value
    if discr & 0x2000:                       # negative?
        discr -= 0x4000
    return f"corr={corr}  discr={discr}"


DECODER = {
    REG_6001: _decode_mask,
    REG_6002: _decode_6002,
    REG_6003: _decode_mask,
    REG_6004: _decode_mask,
    REG_6010: _decode_6010,
    REG_6100: _decode_6100,
}


# ---------- pretty print ---------------------------------------------------
def _pretty(ip: str, raw_vals: dict[int, int | None]) -> None:
    tbl = Table(
        title=f"Self-trigger registers  –  {ip}",
        show_header=True, header_style="bold magenta",
    )
    tbl.add_column("Register", justify="right")
    tbl.add_column("Value",    justify="right")
    tbl.add_column("Decoded meaning / fields", justify="left")

    for addr in REG_LIST:
        val = raw_vals[addr]
        val_fmt = "—" if val is None else f"0x{val:x}"
        decoded = DECODER[addr](val)
        tbl.add_row(f"0x{addr:04x}", val_fmt, decoded)

    rich.print(tbl)


# ────────────────────────── public API ─────────────────────────
def check(ips: List[int]) -> None:
    """Dump & decode the self-trigger bank for every endpoint suffix."""
    for suf in ips:
        full_ip = endpoint_ip(suf)
        dev     = Daphne(full_ip)
        try:
            raw = {addr: _read(dev, addr) for addr in REG_LIST}
            _pretty(full_ip, raw)
        finally:
            dev.close()
