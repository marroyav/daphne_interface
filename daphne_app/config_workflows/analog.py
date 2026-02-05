# daphne_app/config_workflows/analog.py
from __future__ import annotations
"""
Write / read the analogue chain (offset DACs, coarse gain, VGA).

• configure(…) – offsets / gains / attenuators (VGAIN)
• read(…)      – dump everything in Rich tables

No dependency on *ivtools* any longer – we only use the in-package
`daphne_app.hardware.daphne.Daphne`.
"""

# ───────────────────────────────── standard / 3rd-party ──────────────────────────────
import re
import sys
from collections.abc import Iterable, Sequence
from typing import List

from rich.console import Console
from rich.table import Table
from tqdm import tqdm

# ─────────────────────────────────────  local  ───────────────────────────────────────
from daphne_app.hardware.daphne import Daphne
from daphne_app.utils.ip_utils import endpoint_ip
from daphne_app.utils.register_decode import pretty_print

console = Console()

# ───────────────────────── helpers ──────────────────────────


def _chk_len(name: str, arr: Sequence[int], expect: int) -> None:
    if len(arr) != expect:
        raise ValueError(f"{name} length {len(arr)} ≠ {expect}")


def _afe_set(indices: Sequence[int]) -> set[int]:
    """Return the *AFE* indices touched by *indices* (global CH numbers)."""
    return {ch // 8 for ch in indices}


# ──────────────────── regexes reused from analog_check.py ──────────────────
_OFFSET_PAT = re.compile(r"OFFSET DAC REG=\s*(\d+).*DAC GAIN=(\d+)")
_REG_PAT    = re.compile(r"REG\s*([0-9A-Fa-fx]+)\s*=\s*([0-9A-Fa-fx]+)")
_VGAIN_PAT  = re.compile(r"VGAIN DAC REG=\s*(\d+).*DAC GAIN=(\d+)")
_SPI_MAP    = {4: 0x04, 51: 0x33, 52: 0x34}

# ─────────────────────────── AFE register helpers ──────────────────────────
_ADC_RES_MASK = 1 << 1
_ADC_OUT_MASK = 1 << 3
_BIT_ORDER_MASK = 1 << 4

_LPF_MASK = 0b111 << 1
_PGA_INT_MASK = 1 << 4
_PGA_GAIN_MASK = 1 << 13

_LNA_CLAMP_MASK = 0b11 << 9
_LNA_INT_MASK = 1 << 12
_LNA_GAIN_MASK = 0b11 << 13


def _set_bits(value: int, mask: int, shift: int, raw: int) -> int:
    return (value & ~mask) | ((raw << shift) & mask)


def _read_afe_reg(dev: Daphne, afe: int, reg: int) -> int:
    resp = dev.command(f"RD AFE {afe} REG {reg}")
    m = _REG_PAT.search(resp)
    if not m:
        raise ValueError(f"Failed to parse AFE{afe} REG {reg}: {resp!r}")
    return int(m.group(2), 0)


def _encode_lpf(lpf: int) -> int:
    # allow either coded values or MHz-ish numbers used in configs
    mapping = {15: 0b000, 20: 0b010, 30: 0b011, 10: 0b100, 4: 0b100}
    if lpf in mapping:
        return mapping[lpf]
    if 0 <= lpf <= 7:
        return lpf
    raise ValueError(f"Unsupported lpf_cut_frequency: {lpf}")


# ─────────────────────────── public API ────────────────────────────────────
def configure(
    ips: Iterable[int],
    *,
    offsets: Sequence[int] | None = None,
    gains: Sequence[int] | None = None,
    attenuators: Sequence[int] | None = None,   # AKA VGAIN
    vgains: Sequence[int] | None = None,        # compatibility alias
    only_indices: Sequence[int] | None = None,
    progress: bool | str = "auto",
    offset_mv: int = 2250,
    gain: int = 1,
    vgain: int = 0,
    # optional AFE register config (ADC/PGA/LNA)
    adc_resolution: int | None = None,
    adc_output_format: int | None = None,
    adc_sb_first: int | None = None,
    pga_lpf_cut_frequency: int | None = None,
    pga_integrator_disable: int | None = None,
    pga_gain: int | None = None,
    lna_clamp: int | None = None,
    lna_integrator_disable: int | None = None,
    lna_gain: int | None = None,
) -> None:
    """
    Configure OFFSET DACs, coarse gains and VGA attenuators.
    Optionally programs AFE SPI registers (ADC/PGA/LNA) when values are given.

    `attenuators` and `vgains` are synonyms so existing JSON files that
    carry `"attenuators"` work unchanged.
    """
    if attenuators is None:
        attenuators = vgains

    all_ch = list(range(40))
    only_indices = list(only_indices or all_ch)
    n_ch = len(only_indices)

    # vectors ----------------------------------------------------------------
    offsets = list(offsets) if offsets is not None else [offset_mv] * n_ch
    gains   = list(gains)   if gains   is not None else [gain]     * n_ch
    _chk_len("offsets", offsets, n_ch)
    _chk_len("gains",   gains,   n_ch)

    afe_used = sorted(_afe_set(only_indices))
    if attenuators is None:
        attenuators = [vgain] * len(afe_used)
    _chk_len("attenuators", attenuators, len(afe_used))
    vgain_map = dict(zip(afe_used, attenuators))

    # ------------------------------------------------------------------------
    for suf in ips:
        ip = endpoint_ip(suf)
        dev = Daphne(ip)

        use_bar = progress if isinstance(progress, bool) else sys.stdout.isatty()
        ch_iter = tqdm(only_indices, desc=f"Channels {ip}", unit="ch") if use_bar else only_indices

        # per-channel config
        for idx, ch in enumerate(ch_iter):
            dev.command(f"WR OFFSET CH {ch} V {offsets[idx]}")
            dev.command(f"CFG OFFSET CH {ch} GAIN {gains[idx]}")

        # per-AFE VGA
        for afe, v in vgain_map.items():
            dev.command(f"WR AFE {afe} VGAIN V {v}")

        # optional AFE register programming (ADC/PGA/LNA)
        if any(
            v is not None
            for v in (
                adc_resolution,
                adc_output_format,
                adc_sb_first,
                pga_lpf_cut_frequency,
                pga_integrator_disable,
                pga_gain,
                lna_clamp,
                lna_integrator_disable,
                lna_gain,
            )
        ):
            for afe in afe_used:
                # REG 4 (0x04): ADC config
                reg4 = _read_afe_reg(dev, afe, 4)
                if adc_resolution is not None:
                    reg4 = _set_bits(reg4, _ADC_RES_MASK, 1, int(adc_resolution) & 0x1)
                if adc_output_format is not None:
                    reg4 = _set_bits(reg4, _ADC_OUT_MASK, 3, int(adc_output_format) & 0x1)
                if adc_sb_first is not None:
                    reg4 = _set_bits(reg4, _BIT_ORDER_MASK, 4, int(adc_sb_first) & 0x1)
                dev.command(f"WR AFE {afe} REG 4 V {reg4}")

                # REG 51 (0x33): PGA config
                reg51 = _read_afe_reg(dev, afe, 51)
                if pga_lpf_cut_frequency is not None:
                    reg51 = _set_bits(reg51, _LPF_MASK, 1, _encode_lpf(int(pga_lpf_cut_frequency)))
                if pga_integrator_disable is not None:
                    reg51 = _set_bits(reg51, _PGA_INT_MASK, 4, int(pga_integrator_disable) & 0x1)
                if pga_gain is not None:
                    reg51 = _set_bits(reg51, _PGA_GAIN_MASK, 13, int(pga_gain) & 0x1)
                dev.command(f"WR AFE {afe} REG 51 V {reg51}")

                # REG 52 (0x34): LNA config
                reg52 = _read_afe_reg(dev, afe, 52)
                if lna_clamp is not None:
                    reg52 = _set_bits(reg52, _LNA_CLAMP_MASK, 9, int(lna_clamp) & 0x3)
                if lna_integrator_disable is not None:
                    reg52 = _set_bits(reg52, _LNA_INT_MASK, 12, int(lna_integrator_disable) & 0x1)
                if lna_gain is not None:
                    reg52 = _set_bits(reg52, _LNA_GAIN_MASK, 13, int(lna_gain) & 0x3)
                dev.command(f"WR AFE {afe} REG 52 V {reg52}")

        console.print(f"[green]✓ Analog chain configured on {ip} (VGA={vgain_map})[/]")
        dev.close()


# ──────────────────────────────  reader  ──────────────────────────────────
def _parse_reg_val(text: str, pat: re.Pattern[str]) -> int | None:
    m = pat.search(text)
    return int(m.group(1)) if m else None


def read(
    ips: Iterable[int],
    *,
    only_indices: Sequence[int] | None = None,
) -> None:
    """
    Read back offsets / gains plus AFE register block (0x04, 0x33, 0x34, VGAIN).

    Everything is printed in Rich tables – no *ivtools* needed anymore.
    """
    all_ch = list(range(40))
    indices = list(only_indices or all_ch)

    for suf in ips:
        ip = endpoint_ip(suf)
        dev = Daphne(ip)
        console.rule(ip)

        # ── channel table ────────────────────────────────────────────────
        tbl = Table(title="Channel offsets", header_style="bold cyan")
        tbl.add_column("CH", justify="right")
        tbl.add_column("Offset", justify="right")
        tbl.add_column("Gain",   justify="right")

        for ch in indices:
            resp = dev.command(f"RD OFFSET CH {ch}")
            m = _OFFSET_PAT.search(resp)
            if m:
                off, g = m.groups()
                tbl.add_row(f"{ch:02}", off, g)
            else:
                tbl.add_row(f"{ch:02}", "err", "err")
        console.print(tbl)

        # ── AFE register tables ─────────────────────────────────────────
        for afe in range(5):
            reg_table = Table(
                title=f"AFE{afe} registers", header_style="bold cyan"
            )
            reg_table.add_column("Reg", width=6)
            reg_table.add_column("Raw", width=8, style="magenta")
            reg_table.add_column("Field", width=18, style="yellow")
            reg_table.add_column("Meaning")

            # SPI registers 0x04, 0x33, 0x34
            for reg in (4, 51, 52):
                resp = dev.command(f"RD AFE {afe} REG {reg}")
                m = _REG_PAT.search(resp)
                if not m:
                    reg_table.add_row(f"{reg:#04x}", "err", "", "<parse error>")
                    continue

                value = int(m.group(2), 0)
                spi_addr = _SPI_MAP[reg]

                first = True
                for line in pretty_print.__self__.decode(spi_addr, value):
                    field, meaning = line.split("= ")
                    field, meaning = field.strip(), meaning.strip()
                    if first:
                        reg_table.add_row(f"{reg:#04x}", f"0x{value:04X}", field, meaning)
                        first = False
                    else:
                        reg_table.add_row("", "", field, meaning)

            # VGAIN
            resp = dev.command(f"RD AFE {afe} VGAIN")
            m = _VGAIN_PAT.search(resp)
            if m:
                vreg, vgain = m.groups()
                reg_table.add_row("VGAIN", f"0x{int(vreg):04X}", "DAC_REG", f"{vreg}  GAIN={vgain}")
            else:
                reg_table.add_row("VGAIN", "err", "", "<parse error>")

            console.print(reg_table)

        dev.close()
