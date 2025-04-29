"""
Utility helpers to convert between a DAPHNE “endpoint suffix”
(slot-ID, 4 → 10.73.137.104, etc.) and the full IP string.

Older code used `_endpoint_ip`; newer code prefers `endpoint_ip`
and `ip_suffix`.  All three names are exported for compatibility.
"""

from __future__ import annotations

# Change here if the network prefix ever moves.
NETWORK_PREFIX = "10.73.137."

__all__ = [
    "endpoint_ip",
    "ip_suffix",
    "_endpoint_ip",   # ← legacy helper kept for backward compatibility
]

# ────────────────────────────────────────────────────────────────────
# Conversions
# ────────────────────────────────────────────────────────────────────
def _endpoint_ip(suffix: int) -> str:
    """
    Legacy helper (kept so existing imports keep working).
    """
    return f"{NETWORK_PREFIX}{100 + int(suffix)}"


def endpoint_ip(suffix: int | str) -> str:
    """
    Convert a slot suffix (e.g. 7) to its full IP address.

    Example
    -------
    >>> endpoint_ip(4)
    '10.73.137.104'
    >>> endpoint_ip("9")
    '10.73.137.109'
    """
    return _endpoint_ip(int(suffix))


def ip_suffix(addr: str | int) -> int:
    """
    The inverse of `endpoint_ip` – extract the slot suffix from a
    full address *or* pass-through if an int is already supplied.

    Example
    -------
    >>> ip_suffix("10.73.137.107")
    7
    >>> ip_suffix(12)
    12
    """
    # Already an integer?  Assume the caller gave us a suffix.
    if isinstance(addr, int):
        return addr

    if not addr.startswith(NETWORK_PREFIX):
        raise ValueError(
            f"IP '{addr}' does not start with expected prefix '{NETWORK_PREFIX}'"
        )

    return int(addr.split(".")[-1]) - 100
