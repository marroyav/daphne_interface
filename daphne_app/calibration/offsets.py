# daphne_app/calibration/offsets.py
"""
Robust PGA *offset-DAC* calibration
===================================

The algorithm is self-centering and works directly with the full IPv4
stored in *details.json*.

Workflow
--------
1.  Initial DACs are read from the board (fallback 2250).
2.  Each iteration acquires *n_wf* spy-buffer wave-forms per channel,
    computes the **median baseline** on the first PRE_PULSE_WIN samples
    and steers the DAC until |error| ≤ band.
3.  Step adaptation:
       – first step = *step_init*
       – overshoot  → step //= 2  (≥ 4)
       – stuck on rail → step *= 2 (≤ rail)
4.  The best (min-error) DAC is stored; a log, PNG plot and optional
    JSON map are written at the end.

Default DAC limits are widened to 1500 … 3000 counts.
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm  # noqa: F401 — kept for a future progress-bar
from daphne_app.hardware.daphne import Daphne

# ────────────────────────── constants ────────────────────────────
OFFSET_MIN     = 1500
OFFSET_MAX     = 3000
DAC_FALLBACK   = 2250
PRE_PULSE_WIN  = 4000            # samples used for the baseline median
OFFSET_RE = re.compile(r"OFFSET DAC REG=\s*(\d+)")


# ────────────────────────── helpers ──────────────────────────────
def _read_dac(dev: Daphne, ch: int) -> int:
    """Ask the board for the current OFFSET DAC value – with fallback."""
    try:
        txt = dev.command(f"RD OFFSET CH {ch}")
        dac = int(OFFSET_RE.search(txt).group(1))
    except Exception:
        dac = DAC_FALLBACK
    return int(np.clip(dac, OFFSET_MIN, OFFSET_MAX))


def _acquire_baseline(
    dev: Daphne, *, afe: int, ch: int, n_wf: int, n_samples: int
) -> float:
    """
    Trigger *n_wf* times, read ``n_samples`` points each time and return
    the **median** of the first ``PRE_PULSE_WIN`` samples over the stack.
    """
    waves: list[np.ndarray] = []
    for _ in range(n_wf):
        wf = dev.read_waveform(
            afe=afe, ch=ch, samples=n_samples, self_trigger=True
        )
        if wf.size:
            waves.append(wf[:PRE_PULSE_WIN])

    if not waves:
        return np.nan
    flat = np.concatenate(waves)
    return float(np.median(flat))


# ---------------- details.json loader ------------------------------------
def channels_from_json(
    file: str | Path,
) -> Tuple[str, Dict[int, List[int]], Set[int]]:
    """
    Parse *details.json* and return

    • full IPv4 string
    • dict {AFE: [local channels]}
    • set() of inverted global channels
    """
    cfg = json.loads(Path(file).read_text())
    dev = cfg["devices"][0]

    full_ip: str = dev["ip"]

    ch_per_afe: Dict[int, List[int]] = defaultdict(list)
    for glob in dev["channels"]["indices"]:
        afe, loc = divmod(glob, 8)
        ch_per_afe[afe].append(loc)

    inverted = set(dev["self_trigger"].get("enable_inverter", []))
    return full_ip, dict(ch_per_afe), inverted


# ────────────────────────── main calibrator ──────────────────────
def run(
    *,
    full_ip: str,
    channels_per_afe: Dict[int, List[int]],
    inverted_glob: Set[int],
    target: int,
    band: int,
    samples: int,
    n_wf: int,
    max_iters: int,
    step_init: int,
    step_min: int,
    save_json: Path | None,
) -> None:
    """Entry-point used by the Typer CLI."""
    dev = Daphne(full_ip)

    STEP_MIN=step_min
    # -------- logging --------
    log_name = f"offset_calib_{full_ip.replace('.', '_')}.log"
    logging.basicConfig(
        filename=log_name,
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    log = logging.getLogger("offset_calib")
    log.info("Calibration started for %s", full_ip)

    # -------- bookkeeping --------
    glob_ch = sorted(
        afe * 8 + ch for afe, lst in channels_per_afe.items() for ch in lst
    )
    dac_now  = {g: _read_dac(dev, g) for g in glob_ch}
    step     = {g: step_init         for g in glob_ch}
    locked   = {g: False             for g in glob_ch}
    best_dac = {g: dac_now[g]        for g in glob_ch}
    best_err = {g: float("inf")      for g in glob_ch}
    hist_err: Dict[int, list[float]] = {g: [] for g in glob_ch}

    for g in glob_ch:
        log.info("CH%02d  start DAC %d  inverted=%s", g, dac_now[g], g in inverted_glob)

    # -------- main loop --------
    for it in range(1, max_iters + 1):
        log.info("--- iteration %d ---", it)
        for g in glob_ch:
            if locked[g]:
                continue

            afe, loc = divmod(g, 8)
            mean = _acquire_baseline(dev, afe=afe, ch=loc,
                                     n_wf=n_wf, n_samples=samples)
            if np.isnan(mean):
                log.warning("CH%02d  no data → skipped", g)
                continue

            error = target - mean
            if g in inverted_glob:
                error *= -1

            # remember best
            if abs(error) < best_err[g]:
                best_err[g] = abs(error)
                best_dac[g] = dac_now[g]

            # lock?
            if abs(error) <= band:
                locked[g] = True
                log.info("CH%02d  locked @ %d  err=%+.1f", g, dac_now[g], error)
                continue

            # step adaptation
            sign = np.sign(error)
            if hist_err[g] and np.sign(hist_err[g][-1]) != sign:
                step[g] = max(STEP_MIN, step[g] // 2)        # overshoot
            elif dac_now[g] in (OFFSET_MIN, OFFSET_MAX):
                step[g] = max(STEP_MIN, min(step[g] * 2, 256))  # rail, grow but cap

            new_dac = int(np.clip(dac_now[g] + sign * step[g],
                                  OFFSET_MIN, OFFSET_MAX))
            dev.command(f"WR OFFSET CH {g} V {new_dac}")
            dac_now[g] = new_dac
            hist_err[g].append(error)

            log.info(
                "CH%02d  %s→ %d  err=%+.1f  step=%3d  %s",
                g,
                "flip " if len(hist_err[g]) > 1 and
                np.sign(hist_err[g][-2]) != sign else "",
                new_dac,
                error,
                step[g],
                "coarse" if step[g] > 32 else "fine",
            )

        if all(locked.values()):
            log.info("🎯 all channels locked – stopping early")
            break

    # -------- summary --------
    log.info("=== best DAC map ===")
    for g in glob_ch:
        log.info("CH%02d %d", g, best_dac[g])

    if save_json:
        Path(save_json).write_text(json.dumps(best_dac, indent=2))
        log.info("Best DACs written to %s", save_json)

    # -------- plot --------
    plt.figure(figsize=(10, 4.5))
    for g, errs in hist_err.items():
        if errs:
            plt.plot(errs, label=f"CH{g:02}", alpha=0.7)
    plt.axhline(band,  color="k", ls="--")
    plt.axhline(-band, color="k", ls="--")
    plt.xlabel("iteration")
    plt.ylabel("target − mean  [ADC]")
    plt.title(f"DAPHNE offset convergence  ({full_ip})")
    if any(hist_err[g] for g in glob_ch):
        plt.legend(ncol=4, fontsize=8)
    plt.grid(True, ls=":")
    fname = f"offset_calib_{full_ip.replace('.', '_')}.png"
    plt.tight_layout(); plt.savefig(fname, dpi=300)
    log.info("Convergence plot saved to %s", fname)
