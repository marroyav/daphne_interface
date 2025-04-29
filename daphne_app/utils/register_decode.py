# daphne_app/utils/register_decode.py
# ----------------------------------
"""
Translate raw SPI-register words into human-readable fields for
registers 0x04, 0x33 and 0x34 (you can add more easily).

Usage
-----
>>> from daphne_app.utils.register_decode import pretty_print
>>> pretty_print(0x34, 0x2081)
"""

from collections import namedtuple

Field = namedtuple("Field", "mask shift label options")


def _bitmask(msb: int, lsb: int = 0) -> int:
    """Return a bit-mask covering bits [msb:lsb] inclusive."""
    return ((1 << (msb - lsb + 1)) - 1) << lsb


# ---------------------------------------------------------------------
#  Lookup table
# ---------------------------------------------------------------------
DECODER = {
    # ------------- Register 0x04 -------------------------------------
    0x04: [
        Field(_bitmask(1), 1, "ADC_RESOLUTION", {0: "14-bit", 1: "12-bit"}),
        Field(_bitmask(3), 3, "ADC_OUT_FMT",    {0: "2’s comp", 1: "Offset bin"}),
        Field(_bitmask(4), 4, "BIT_ORDER",      {0: "LSB first", 1: "MSB first"}),
    ],
    # ------------- Register 0x33 (Reg 51) ----------------------------
    0x33: [
        Field(_bitmask(0), 0, "RESERVED", {0: "0"}),
        Field(_bitmask(3, 1), 1, "LPF_PROGRAM", {
            0b000: "15 MHz", 0b010: "20 MHz",
            0b011: "30 MHz", 0b100: "10 MHz"}),
        Field(_bitmask(4), 4, "PGA_INTG_DIS", {0: "Enable", 1: "Disable"}),
        Field(_bitmask(7, 5), 5, "PGA_CLAMP", {
            0b000: "–2 dBFS", 0b010: "0 dBFS",
            0b100: "–2 dBFS (LP/MP)", 0b110: "0 dBFS (LP/MP)"}),
        Field(_bitmask(13), 13, "PGA_GAIN_CTL", {0: "24 dB", 1: "30 dB"}),
    ],
    # ------------- Register 0x34 (Reg 52) ----------------------------
    0x34: [
        Field(_bitmask(4, 0), 0, "TERM_RES_CODE",
              {i: f"Code {i}" for i in range(32)}),  # Table 8 mapping
        Field(_bitmask(5), 5, "IND_RES_EN", {0: "Off", 1: "On"}),
        Field(_bitmask(7, 6), 6, "PRESET_TERM", {
            0b00: "50 Ω", 0b01: "100 Ω", 0b10: "200 Ω", 0b11: "400 Ω"}),
        Field(_bitmask(8), 8, "TERM_ENABLE", {0: "Off", 1: "On"}),
        Field(_bitmask(10, 9), 9, "LNA_CLAMP_SET", {
            0b00: "Auto", 0b01: "1.5 Vpp",
            0b10: "1.15 Vpp", 0b11: "0.6 Vpp"}),
        Field(_bitmask(12), 12, "LNA_INTG_DIS", {0: "Enable", 1: "Disable"}),
        Field(_bitmask(14, 13), 13, "LNA_GAIN", {
            0b00: "18 dB", 0b01: "24 dB", 0b10: "12 dB", 0b11: "Resv"}),
        Field(_bitmask(15), 15, "LNA_CH_CNTL", {0: "Off", 1: "On"}),
    ],
}


# ---------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------
def decode(reg_addr: int, value: int) -> list[str]:
    """Return list of 'label = meaning (raw)' strings."""
    lines: list[str] = []
    for field in DECODER.get(reg_addr, []):
        raw = (value & field.mask) >> field.shift
        meaning = field.options.get(raw, f"?? ({raw})")
        lines.append(f"{field.label:<16}= {meaning:<12} ({raw:#x})")
    return lines


def pretty_print(reg_addr: int, value: int) -> None:
    """Print decoded register fields to stdout."""
    print(f"\nRegister 0x{reg_addr:02X} value 0x{value:04X}")
    for line in decode(reg_addr, value):
        print("  •", line)
