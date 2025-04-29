from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Any, TypedDict


class SelfTrigCfg(TypedDict, total=False):
    threshold: int
    filter_mode: str
    slope_mode: str
    slope_threshold: int
    pedestal_length: int
    spybuffer_channel: int
    self_trigger_xcorr: Dict[str, int]
    enable_compensator: List[int]
    enable_inverter: List[int]


class DeviceCfg(TypedDict):
    ip: str
    slot_id: int
    det_id: int
    version: int
    mode: str
    self_trigger: SelfTrigCfg
    channels: Dict[str, Any]


class DaphneJsonCfg(TypedDict):
    metadata: Dict[str, Any]
    common_conf: Dict[str, Any]
    devices: List[DeviceCfg]


def load(path: Path) -> DaphneJsonCfg:
    """Read and return a validated JSON configuration."""
    data: Any = json.loads(path.read_text())
    if not isinstance(data, dict) or "devices" not in data:
        raise ValueError("Invalid DAPHNE JSON (missing 'devices').")
    return data  # type: ignore[return-value]
