# daphne_app/calibration/offsets.py

"""
Strategy
--------
1.  **Initial state**
    • Endpoint IP and list of (AFE,CH) pairs come from *details.json*
      (`devices[0].channels.indices`).
    • Set *inverted* flag automatically for every global channel that
      appears in `devices[0].self_trigger.enable_inverter`.
    • Query each channel with `RD OFFSET CH <n>` and use the current DAC
      as starting point (fallback 2250).

2.  **Iterative loop (≤ max_iters, default 7)**
    a. Trigger the spy-buffer, collect *n_wf* wave-forms, compute the
       baseline mean.
    b. Error := TARGET − mean (flipped for inverted channels).
    c. If `|error| ≤ band` → **lock** channel, no more writes.
    d. Else
       – On first iteration use an **initial step** (`--step-init`, default 50).
       – Whenever the sign of *error* flips between iterations,
         `step ← max(1, step/2)`.
       – New_DAC = clip( old_DAC + sign(error)·step, 2000…2500 ),
         write with `WR OFFSET CH <n> V <new_dac>`.
    e. Track the “best” (DAC, |error|) pair for every channel.

3.  **Termination**
    • Stops early when every channel is locked, or after *max_iters*.
    • Prints / logs a summary and saves:
        – `offset_calib_<ip>.log`          full text log
        – `offset_calib_<ip>.png`          convergence plot
        – Optional `--save-json best.json`  ⇒  `{"0": 2248, "1": …}`

CLI options
-----------
--target          baseline target in ADC counts                [4000]
--band            lock when |mean−target| ≤ band               [2]
--samples         ADC samples per waveform                      4000
--n-wf            wave-forms per iteration per channel           3
--step-init       initial DAC step (counts)                     50
--max-iters       maximum iterations                             7
--save-json       path to dump best DACs as JSON                None
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, List
import json, re, time, logging

import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm

from daphne_app.hardware.daphne import Daphne
from daphne_app.utils.ip_utils import endpoint_ip, ip_suffix

OFFSET_RE = re.compile(r"OFFSET DAC REG=\s*(\d+)")

# ───────────────────────── helpers ──────────────────────────
def _channels_from_json(details: Path) -> tuple[int, Dict[int, List[int]], set[int]]:
    """Return (ip_suffix, {AFE:[ch,…]}, inverted_global_channels)."""
    cfg  = json.loads(details.read_text())
    dev  = cfg["devices"][0]

    inv_glob: set[int] = set()
    if dev.get("self_trigger", {}).get("enable_inverter"):
        inv_glob = {int(x) for x in dev["self_trigger"]["enable_inverter"]}

    mapping: Dict[int, List[int]] = {}
    for idx in dev["channels"]["indices"]:
        afe, ch = divmod(idx, 8)
        mapping.setdefault(afe, []).append(ch)
    for lst in mapping.values():
        lst.sort()
    return ip_suffix(dev["ip"]), mapping, inv_glob


def _read_initial_dacs(dev: Daphne, glob_ch: List[int]) -> Dict[int, int]:
    """Query the board for existing DAC values (falls back to 2250)."""
    dacs: Dict[int, int] = {}
    for ch in glob_ch:
        try:
            resp = dev.command(f"RD OFFSET CH {ch}")
            m = OFFSET_RE.search(resp)
            dacs[ch] = int(m.group(1)) if m else 2250
        except Exception:
            dacs[ch] = 2250
    return dacs


# ───────────────────── main algorithm ───────────────────────
def run(
    *,
    ip_suffix: int,
    channels_per_afe: Dict[int, List[int]],
    inverted_glob: set[int] = frozenset(),
    target: int   = 4000,
    band:   int   = 2,
    samples: int  = 4000,
    n_wf:    int  = 3,
    max_iters: int = 7,
    step_init: int = 50,
    save_json: Path | None = None,
) -> None:

    full_ip = endpoint_ip(ip_suffix)
    dev     = Daphne(full_ip)

    glob_ch   = [8*afe + ch for afe,chs in channels_per_afe.items() for ch in chs]
    offsets   = _read_initial_dacs(dev, glob_ch)
    steps     = {c: step_init for c in glob_ch}
    locked    = {c: False      for c in glob_ch}
    best_err  = {c: 1e9        for c in glob_ch}   # keep best (min abs err)
    best_dac  = {c: offsets[c] for c in glob_ch}
    history   = {c: []         for c in glob_ch}

    # logging
    logf = f"offset_calib_{full_ip.replace('.','_')}.log"
    logging.basicConfig(
        filename=logf, filemode="w",
        level=logging.INFO,
        format="%(asctime)s | %(message)s",
    )
    console = logging.StreamHandler(); console.setLevel(logging.INFO)
    logging.getLogger().addHandler(console)

    logging.info("Starting offsets: " + ", ".join(
        f"CH{c:02}={d}" for c,d in offsets.items()))

    dt = 16e-9
    for it in range(max_iters):
        logging.info(f"── iteration {it+1}/{max_iters} ──")

        mean_per = {}
        for c in tqdm(glob_ch, desc="WF acquisition", leave=False):
            afe, ch_loc = divmod(c, 8)
            wfs = [dev.read_waveform(afe, ch_loc, samples=samples)
                   for _ in range(n_wf)]
            mean_val = float(np.mean(np.vstack(wfs)[:, :samples]))
            mean_per[c] = mean_val
            history[c].append(mean_val)

        # adjust
        for c, mean_val in mean_per.items():
            if locked[c]:
                continue
            err = target - mean_val
            if c in inverted_glob:
                err *= -1

            # keep best
            if abs(err) < best_err[c]:
                best_err[c], best_dac[c] = abs(err), offsets[c]

            if abs(err) <= band:
                locked[c] = True
                logging.info(f"CH{c:02} locked | mean={mean_val:.1f}")
                continue

            # flip detection → halve step
            if len(history[c]) > 2:
                a,b,curr = history[c][-3:]
                if (curr-b)*(b-a) < 0:
                    steps[c] = max(1, steps[c]//2)

            delta          = int(np.sign(err)*steps[c])
            new_dac        = int(np.clip(offsets[c]+delta, 2000, 2500))
            offsets[c]     = new_dac
            dev.command(f"WR OFFSET CH {c} V {new_dac}")

            logging.info(f"CH{c:02}: mean={mean_val:.1f} err={err:+.1f} "
                         f"→ DAC {new_dac} (step {steps[c]})")

        if all(locked.values()):
            logging.info("🎯 all channels within band — stopping.")
            break
        time.sleep(0.5)

    # summary
    logging.info("Best (min-error) DACs:")
    for c in sorted(best_dac):
        logging.info(f"  CH{c:02}  {best_dac[c]}  (|err|={best_err[c]:.1f})")

    if save_json:
        with Path(save_json).expanduser().open("w") as fh:
            json.dump(best_dac, fh, indent=2)
        logging.info(f"Saved JSON → {save_json}")

    # convergence plot
    plt.figure(figsize=(12,5))
    for c, series in history.items():
        plt.plot(series, label=f"CH{c:02}", alpha=.6)
    plt.axhline(target, ls="--", c="k")
    plt.fill_between(range(len(next(iter(history.values())))),
                     target-band, target+band,
                     color="green", alpha=.15, label="target band")
    plt.xlabel("iteration"); plt.ylabel("baseline [ADC]")
    plt.title(f"Offset tuning  –  endpoint {full_ip}")
    plt.grid(alpha=.3); plt.tight_layout()
    plt.legend(fontsize=8, ncol=4)
    out_png = f"offset_calib_{full_ip.replace('.','_')}.png"
    plt.savefig(out_png, dpi=300); logging.info(f"Plot saved → {out_png}")
