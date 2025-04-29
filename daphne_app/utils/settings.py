"""Centralised configuration loader.

Reads *settings.yaml* shipped inside the package (``daphne_app/config``).
This externalises all magic numbers (valid IPs, data‑mode registers, …)
so operators can tweak them without touching Python code.

Place a file like this alongside this module (``daphne_app/config/settings.yaml``):

```yaml
valid_ips: [4, 5, 6, 7, 9, 10, 11, 12, 13]
full_stream_endpoints: [4, 5, 7]

# Per‑endpoint data‑mode configuration
# (values can be written in hex or decimal)

data_modes:
  "4":  {mode: full_stream,          reg_3000: 0x001081, reg_6001: 0xFFFF}
  "5":  {mode: full_stream,          reg_3000: 0x001081, reg_6001: 0x5A0A5FF}
  "7":  {mode: full_stream,          reg_3000: 0x001081, reg_6001: 0x8040201FF}
  "9":  {mode: hi_rate_self_trigger, reg_3000: 0x001081, reg_6001: 0xFFFFFFFFFF}
  "11": {mode: hi_rate_self_trigger, reg_3000: 0x002081, reg_6001: 0xFFFFFFFFFF}
  "12": {mode: hi_rate_self_trigger, reg_3000: 0x002081, reg_6001: 0xA5FFFFFFFF}
  "13": {mode: hi_rate_self_trigger, reg_3000: 0x002081, reg_6001: 0xA5}
```

If operators want a different threshold default or brand‑new
endpoint, they edit the YAML and reinstall *without* changing code.
"""

from __future__ import annotations

import importlib.resources as pkg_resources
import pathlib
import yaml
from functools import lru_cache
from types import MappingProxyType

# Runtime path to the YAML (package data).  We store it under
# daphne_app/config/settings.yaml
package_name = __name__.rsplit(".", 1)[0]  # daphne_app.utils -> daphne_app
_yaml_path: pathlib.Path | None = None


def _load_yaml() -> dict:  # noqa: D401
    global _yaml_path  # noqa: PLW0603 – path cached here for debugging aid

    with pkg_resources.files(package_name).joinpath("config/settings.yaml").open("rb") as fh:
        _yaml_path = fh.name  # keep for debug prints/logging
        data = yaml.safe_load(fh)

    if not isinstance(data, dict):
        raise TypeError("settings.yaml must contain a top‑level mapping")
    return data


@lru_cache(maxsize=1)
def settings() -> MappingProxyType[str, object]:  # noqa: D401
    """Return settings as **immutable** mapping (cached)."""
    cfg = _load_yaml()
    return MappingProxyType(cfg)


# Convenience wrappers -------------------------------------------------------


def valid_ips() -> list[int]:
    return settings().get("valid_ips", [])


def data_mode(ip: int) -> dict:
    modes = settings().get("data_modes", {})
    return modes[str(ip)]  # KeyError if unknown – fail fast


def is_full_stream(ip: int) -> bool:
    return ip in settings().get("full_stream_endpoints", [])



# --------------------------------------------------------------------
#  Self-trigger helpers
# --------------------------------------------------------------------
def self_trigger_defaults() -> dict:
    """
    Return the `defaults` dict from settings.yaml::self_trigger.
    If the block or key is absent, return an empty dict.
    """
    st = settings().get("self_trigger", {})
    return st.get("defaults", {})


def self_trigger_overrides(ip_suffix: int) -> dict:
    """
    Return overrides for a given endpoint (by suffix as int), e.g. "7".
    Missing entries yield an empty dict.
    """
    st = settings().get("self_trigger", {}).get("endpoints", {})
    return st.get(str(ip_suffix), {})
