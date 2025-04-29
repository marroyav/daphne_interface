"""
Interactive Plotly visualisation of DAPHNE spy-buffer wave-forms
================================================================

Typical CLI usage
-----------------
channels_to_acquire = {
    0: [0, 7],
    1: [0, 7],
    2: [0, 7],
    3: [0, 7],
    4: list(range(8)),
}

daphne capture plotly --details details.json \
                     --samples 1000 --n-wf 50 \
                     --html wf.html \
                     --save-wf waveforms.npz
"""
from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Iterable
import itertools
import importlib.util
import json
import ipaddress
import pickle

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from daphne_app.hardware.daphne import Daphne
from daphne_app.utils.ip_utils import endpoint_ip


# ───────────────────────────────────────── helpers ──────────────────────────────────────────
def _rms(arr: np.ndarray) -> float:
    """Root-mean-square of an int16 waveform in mV (LSB = 1 mV)."""
    return float(np.sqrt(np.mean(arr.astype(float) ** 2)))


def _hex_to_rgba(hx: str, alpha: float) -> str:
    """Convert '#RRGGBB' → 'rgba(r,g,b,alpha)'."""
    hx = hx.lstrip("#")
    r, g, b = (int(hx[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def _colour_cycle(n: int) -> Iterable[str]:
    """Cycling list of 10 colour-blind-friendly hues."""
    default_hex = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
        "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
        "#bcbd22", "#17becf",
    ]
    return itertools.islice(itertools.cycle(default_hex), n)


# ────────────────────────────── I/O helpers (details.json, …) ──────────────────────────────
def info_from_details(json_file: Path | str) -> tuple[str, Dict[int, List[int]]]:
    """
    Parse *details.json* and return

    • full IPv4 address as a string
    • mapping  {AFE: [ch, …]}  with channels sorted
    """
    cfg = json.loads(Path(json_file).read_text())
    dev = cfg["devices"][0]                       # ↰ one board / file

    full_ip = str(ipaddress.ip_address(dev["ip"]))  # validates
    mapping: Dict[int, List[int]] = {}
    for idx in dev["channels"]["indices"]:
        afe, ch = divmod(idx, 8)
        mapping.setdefault(afe, []).append(ch)
    for lst in mapping.values():
        lst.sort()
    return full_ip, mapping


def load_channels_dict(path: Path | str) -> Dict[int, List[int]]:
    """Import a ``channels_to_acquire`` dict from an arbitrary *.py* file."""
    p = Path(path).expanduser().resolve()
    spec = importlib.util.spec_from_file_location("ch_cfg", p)
    mod  = importlib.util.module_from_spec(spec)          # type: ignore[arg-type]
    spec.loader.exec_module(mod)                          # type: ignore[union-attr]
    return getattr(mod, "channels_to_acquire")


# ───────────────────────────────────── main routine ─────────────────────────────────────────
def view(
    *,
    ip_suffix: int,
    channels_per_afe: Dict[int, List[int]],
    samples: int  = 1000,
    n_wf:    int  = 10,
    html:    str  = "waveforms.html",
    save_wf: str | None = None,
) -> None:
    """
    Acquire ``n_wf`` spy-buffer captures for every requested channel and build

    • an interactive Plotly figure (mean ± σ bands + RMS table)
    • *optionally* a compressed dump of the raw wave-forms (``save_wf`` flag).

    Parameters
    ----------
    ip_suffix          board suffix (7 → 10.73.137.107)
    channels_per_afe   mapping like ``{0:[0,7], 1:[0,7], …}``
    samples            ADC samples per capture
    n_wf               # wave-forms per channel
    html               output HTML file
    save_wf            *.npz / *.npy / *.pkl* file for raw data (or ``None``)
    """
    full_ip = endpoint_ip(ip_suffix)
    dev     = Daphne(full_ip)

    afes          = sorted(channels_per_afe.keys())
    uniq_channels = sorted({c for lst in channels_per_afe.values() for c in lst})
    colour_map    = {ch: col for ch, col in zip(uniq_channels,
                                                _colour_cycle(len(uniq_channels)))}

    # bookkeeping
    rms_stats: Dict[str, float] = {}
    dump_dict: Dict[str, List[np.ndarray]] = {}          # for save_wf
    dt = 16e-9                                           # 16 ns / sample

    # ── figure scaffold ----------------------------------------------------
    fig = make_subplots(
        rows=3, cols=3,
        subplot_titles=[*(f"AFE {a}" for a in afes), "RMS statistics"],
        horizontal_spacing=0.05,
        vertical_spacing  =0.12,
        specs=[
            [{"type": "xy"}] * 3,
            [{"type": "xy"}] * 3,
            [{"type": "domain", "colspan": 3}, None, None],
        ],
    )

    # ── data taking + plotting --------------------------------------------
    for idx, afe in enumerate(afes):
        row, col = (1 if idx < 3 else 2), ((idx % 3) + 1)

        for ch in channels_per_afe[afe]:
            colour = colour_map[ch]
            wf_stack = []

            for _ in range(n_wf):
                # minimal trigger to refresh buffers
                dev.write_reg(0x2020, [1234]); dev.write_reg(0x2021, [1234])
                wf = dev.read_waveform(afe=afe, ch=ch, samples=samples)
                wf_stack.append(wf)

                # faint individual trace
                t = np.arange(wf.size) * dt * 1e6  # µs
                fig.add_trace(
                    go.Scatter(
                        x=t, y=wf,
                        mode="lines",
                        line=dict(width=0.6, color=_hex_to_rgba(colour, 0.25)),
                        hoverinfo="skip",
                        showlegend=False,
                    ),
                    row=row, col=col,
                )

            # store raw data
            dump_dict[f"AFE{afe}_CH{ch}"] = wf_stack

            wf_stack = np.vstack(wf_stack)
            mean_wf, std_wf = wf_stack.mean(axis=0), wf_stack.std(axis=0)
            t = np.arange(mean_wf.size) * dt * 1e6

            # ±1 σ band
            fig.add_trace(
                go.Scatter(
                    x=np.concatenate([t, t[::-1]]),
                    y=np.concatenate([mean_wf + std_wf,
                                      (mean_wf - std_wf)[::-1]]),
                    mode="lines",
                    line=dict(width=0),
                    fill="toself",
                    fillcolor=_hex_to_rgba(colour, 0.18),
                    hoverinfo="skip",
                    showlegend=False,
                ),
                row=row, col=col,
            )
            # mean trace
            fig.add_trace(
                go.Scatter(
                    x=t, y=mean_wf,
                    mode="lines",
                    line=dict(width=1.6, color=colour),
                    name=f"CH {ch}",
                    showlegend=False,           # legend intentionally hidden
                ),
                row=row, col=col,
            )

            rms_stats[f"AFE {afe} CH {ch}"] = round(_rms(wf_stack.ravel()), 2)

    # ── RMS statistics table ----------------------------------------------
    hdr, cells = zip(*sorted(rms_stats.items(), key=lambda kv: kv[0]))
    fig.add_trace(
        go.Table(
            header=dict(values=["Channel", "RMS [mV]"],
                        fill_color="lightgrey",
                        font=dict(size=14), align="left"),
            cells=dict(values=[hdr, cells],
                       align="left",
                       font=dict(size=13)),
        ),
        row=3, col=1,
    )

    # ── layout polish ------------------------------------------------------
    fig.update_xaxes(title="time [µs]", row=1, col=1)
    fig.update_yaxes(title="ADC counts", row=1, col=1)
    fig.update_layout(
        template="simple_white",
        height=900, width=1300,
        margin=dict(l=70, r=40, t=80, b=60),
        title=dict(
            text=f"DAPHNE wave-forms — endpoint {full_ip}",
            x=0.01, xanchor="left", font=dict(size=20, family="Helvetica"),
        ),
    )

    out_html = Path(html).expanduser().resolve()
    fig.write_html(out_html, include_mathjax="cdn")
    print(f"🔬  Interactive figure written to {out_html}")

    # ── optional serialisation of raw wave-forms --------------------------
    if save_wf:
        out_wf = Path(save_wf).expanduser().resolve()
        if out_wf.suffix == ".npz":
            np.savez_compressed(out_wf, **dump_dict)
        elif out_wf.suffix == ".npy":
            np.save(out_wf, dump_dict, allow_pickle=True)
        elif out_wf.suffix == ".pkl":
            with out_wf.open("wb") as fh:
                pickle.dump(dump_dict, fh, protocol=pickle.HIGHEST_PROTOCOL)
        else:
            raise ValueError("save_wf must end with .npz, .npy or .pkl")
        print(f"💾  Raw wave-forms saved to {out_wf}")


# ───────────────────────────── standalone entry-point ───────────────────────
if __name__ == "__main__":        # pragma: no cover
    import argparse

    ap = argparse.ArgumentParser(
        description="Plot DAPHNE wave-forms (interactive Plotly)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--details", help="details.json with IP + channels")
    g.add_argument("--channels-file", help="Python file exporting channels_to_acquire")
    ap.add_argument("--ip", type=int,
                    help="endpoint suffix (ignored when --details is used)")
    ap.add_argument("--samples", type=int, default=1000, help="# ADC samples")
    ap.add_argument("--n-wf", type=int, default=10,
                    help="# wave-forms per channel")
    ap.add_argument("--html", default="waveforms.html", help="output HTML")
    ap.add_argument("--save-wf", help="optional .npz/.npy/.pkl dump")

    args = ap.parse_args()

    if args.details:
        full_ip, ch_map = info_from_details(args.details)
        ip_suf = int(full_ip.split(".")[-1])
    else:
        if args.ip is None:
            ap.error("Need --ip when using --channels-file")
        ch_map = load_channels_dict(args.channels_file)
        ip_suf = args.ip

    view(
        ip_suffix        = ip_suf,
        channels_per_afe = ch_map,
        samples          = args.samples,
        n_wf             = args.n_wf,
        html             = args.html,
        save_wf          = args.save_wf,
    )
