# daphne_app/calibration/offsets.py
"""
Robust PGA *offset-DAC* calibration
===================================

The algorithm is now truly “self-centering”:

1.  **Initial state**
    • Endpoint IP, channel list and `enable_inverter` mask come from
      *details.json* (handed over by the CLI helper).
    • Present DACs are read with ``RD OFFSET CH <n>``; fallback 2250.

2.  **Adaptive search** (≤ *max_iters*)
    a. For every unlocked channel acquire *n_wf* wave-forms, compute the
       baseline mean on the first *samples* points.
    b. *Error* := Target – Mean.
       For inverted channels the sign is flipped.
    c. **Lock** when |error| ≤ *band*.
    d. Otherwise choose a **step**:

       ┌ first iteration → *step_init*
       ├ overshoot (sign flip) → step := max(4, step/2)
       └ plateau at a rail → step := max(4, step×2)

       The rail handling guarantees progress when the first guess pushed
       the DAC to its min/max.
    e. New_DAC := clip(old ± step, *OFFSET_MIN* … *OFFSET_MAX*).
       ``WR OFFSET CH <n> V <New_DAC>``

3.  The smallest |error| observed for every channel is remembered as
    *best DAC*.  At the end a JSON dump, PNG convergence plot and a
    full text log are produced.

Default boundaries have been widened to **1500 … 3000** (covers the
useful DAC range on most boards).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Set
import json, re, time, logging

import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm

from daphne_app.hardware.daphne import Daphne
from daphne_app.utils.ip_utils import endpoint_ip

# ---------- user-tuneable constants ---------------------------------------
OFFSET_MIN = 1500
OFFSET_MAX = 3000
DAC_FALLBACK = 2250            # used when RD OFFSET fails / regex miss

OFFSET_RE = re.compile(r"OFFSET DAC REG=\s*(\d+)")

# ---------- helpers -------------------------------------------------------
def _read_dac(dev: Daphne, ch: int) -> int:
    """RD OFFSET CH <n>  → Extract current DAC or fallback"""
    try:
        txt = dev.command(f"RD OFFSET CH {ch}")
        dac = int(OFFSET_RE.search(txt).group(1))
    except Exception:
        dac = DAC_FALLBACK
    return np.clip(dac, OFFSET_MIN, OFFSET_MAX)

# --------------------------------------------------------------------------
def run(
    *,
    ip_suffix: int,
    channels_per_afe: Dict[int, List[int]],
    inverted_glob: Set[int],
    target: int,
    band: int,
    samples: int,
    n_wf: int,
    max_iters: int,
    step_init: int,
    save_json: Path | None,
) -> None:

    full_ip = endpoint_ip(ip_suffix)
    dev     = Daphne(full_ip)

    logging.basicConfig(
        filename=f"offset_calib_{full_ip}.log",
        level=logging.INFO,
        format="%(levelname)s:%(name)s:%(message)s",
    )
    log = logging.getLogger("offset_calib")
    log.info("Calibration started for %s", full_ip)

    # -------- bookkeeping --------------------------------------------------
    chan_glob = sorted(
        afe * 8 + ch for afe, lst in channels_per_afe.items() for ch in lst
    )

    dac_now   = {g: _read_dac(dev, g) for g in chan_glob}
    step      = {g: step_init        for g in chan_glob}
    locked    = {g: False            for g in chan_glob}
    best_dac  = {g: dac_now[g]       for g in chan_glob}
    best_err  = {g: 99999.           for g in chan_glob}

    history: dict[int, list[float]] = {g: [] for g in chan_glob}

    # print / log starting values
    for g in chan_glob:
        inv = g in inverted_glob
        log.info("CH%02d  start DAC %d  inverted=%s", g, dac_now[g], inv)

    # -------- helper lambdas ----------------------------------------------
    def _acquire_mean(g: int) -> float:
        afe, ch = divmod(g, 8)
        wfs = []
        for _ in range(n_wf):
            dev.write_reg(0x2020, [1234]); dev.write_reg(0x2021, [1234])
            wf = dev.read_waveform(afe, ch, samples=samples)
            if wf.size:
                wfs.append(wf)
        return float(np.mean(wfs)) if wfs else np.nan

    # -------- main loop ----------------------------------------------------
    for it in range(1, max_iters + 1):
        log.info("--- iteration %d ---", it)
        for g in chan_glob:

            if locked[g]:
                continue

            mean = _acquire_mean(g)
            if np.isnan(mean):
                log.warning("CH%02d  no data – skipped", g)
                continue

            error = target - mean
            if g in inverted_glob:
                error *= -1

            # remember best
            if abs(error) < best_err[g]:
                best_err[g] = abs(error)
                best_dac[g] = dac_now[g]

            # lock ?
            if abs(error) <= band:
                locked[g] = True
                log.info("CH%02d  locked @ %d (err=% .1f)", g, dac_now[g], error)
                continue

            # adapt step
            sign = np.sign(error)
            if history[g] and np.sign(history[g][-1]) != sign:
                step[g] = max(4, step[g] // 2)          # overshoot → shrink
            elif dac_now[g] in (OFFSET_MIN, OFFSET_MAX):
                step[g] = max(4, step[g] * 2)           # stuck on rail → grow

            new_dac = int(np.clip(dac_now[g] + sign * step[g], OFFSET_MIN, OFFSET_MAX))
            dev.command(f"WR OFFSET CH {g} V {new_dac}")
            dac_now[g] = new_dac
            history[g].append(error)

            coarse_fine = "coarse" if step[g] > 32 else "fine"
            flip_txt    = "flip " if len(history[g])>=2 and np.sign(history[g][-2])!=sign else ""
            log.info("CH%02d  %s→ %d  err=% .1f  step=%4d  %s",
                     g, flip_txt, new_dac, error, step[g], coarse_fine)

        if all(locked.values()):
            log.info("All channels locked – early stop")
            break

    # -------- summary & artefacts -----------------------------------------
    log.info("=== best DAC map ===")
    for g in chan_glob:
        log.info("CH%02d %d", g, best_dac[g])

    if save_json:
        js = {str(k): int(v) for k, v in best_dac.items()}
        Path(save_json).write_text(json.dumps(js, indent=2))
        log.info("Best DACs written to %s", save_json)

    # convergence plot ------------------------------------------------------
    plt.figure(figsize=(11,5))
    for g, err_list in history.items():
        if err_list:
            plt.plot(err_list, label=f"CH{g:02}")
    plt.axhline( band, color="k", ls="--")
    plt.axhline(-band, color="k", ls="--")
    plt.xlabel("iteration")
    plt.ylabel("target – mean  [ADC]")
    plt.title(f"Offset convergence  {full_ip}")
    plt.grid(True, ls=":")
    if history and any(history[g] for g in chan_glob):
        plt.legend(ncol=4, fontsize=8)
    png = Path(f"offset_calib_{full_ip}.png")
    plt.tight_layout(); plt.savefig(png, dpi=300)
    log.info("Convergence plot saved to %s", png)
