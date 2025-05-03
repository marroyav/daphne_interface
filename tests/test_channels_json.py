# tests/test_channels_json.py
"""
Unit-test for calibration.channels_from_json
-------------------------------------------

Creates a tiny synthetic *details.json*, feeds it to the parser and
checks that:

1. The **full IPv4** string is returned.
2. Channels are grouped by AFE correctly.
3. The set of inverted global channels is respected.
"""

from pathlib import Path
import json

from daphne_app.calibration.offsets import channels_from_json


def test_json_parser(tmp_path: Path):
    fake_details = {
        "devices": [
            {
                "ip": "10.73.137.107",
                "channels": {"indices": [0, 7, 8]},        # 0,7 → AFE0  | 8 → AFE1
                "self_trigger": {"enable_inverter": [8]},  # just one inverted
            }
        ]
    }

    file = tmp_path / "details.json"
    file.write_text(json.dumps(fake_details))

    full_ip, ch_map, inv_set = channels_from_json(file)

    # 1️⃣  full endpoint address
    assert full_ip == "10.73.137.107"

    # 2️⃣  channels grouped per AFE
    #     0  and 7  → global 0 & 7  → AFE0 local 0,7
    #     8         → global 8      → AFE1 local 0
    assert ch_map == {0: [0, 7], 1: [0]}

    # 3️⃣  inverted channels set
    assert inv_set == {8}
