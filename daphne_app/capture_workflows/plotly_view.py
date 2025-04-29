"""
Interactive Plotly visualisation of DAPHNE wave-forms.

Example
-------
channels_to_acquire = {
    0: [0, 7],
    1: [0, 7],
    2: [0, 7],
    3: [0, 7],
    4: list(range(8)),
}

daphne capture plotly --ip 7 --afes 0,1,2,3,4 \
                      --channels-file my_channels.py \
                      --samples 1000 --n 50 --html wf.html
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Iterable
import itertools
import importlib.util
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from daphne_app.hardware.daphne import Daphne
from daphne_app.utils.ip_utils import endpoint_ip

# ─────────────── helpers  ──────────────────────────────────────────────────
def _info_from_details(json_file: str) -> tuple[str, dict[int, list[int]]]:
    """
    Read *details.json* and return
      full_ip  (e.g. "10.73.137.107")
      channels_per_afe  {0: [0,7], 1: [0,7], …}
    """
    import json, ipaddress

    with open(json_file, "r") as f:
        cfg = json.load(f)

    dev = cfg["devices"][0]                # → extend if several boards
    full_ip = str(ipaddress.ip_address(dev["ip"]))   # validates the address

    indices = dev["channels"]["indices"]
    mapping: dict[int, list[int]] = {}
    for idx in indices:
        afe, ch = divmod(idx, 8)
        mapping.setdefault(afe, []).append(ch)
    for lst in mapping.values():
        lst.sort()

    return full_ip, mapping
# ─────────────── utilities ──────────────────────────────────────────────────
def _rms(arr: np.ndarray) -> float:
    return float(np.sqrt(np.mean(arr.astype(float) ** 2)))


def _hex_to_rgba(hx: str, alpha: float) -> str:
    hx = hx.lstrip("#")
    r, g, b = (int(hx[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def _colour_cycle(n: int) -> Iterable[str]:
    default_hex = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
        "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
        "#bcbd22", "#17becf",
    ]
    return itertools.islice(itertools.cycle(default_hex), n)


# ─────────────── main routine ───────────────────────────────────────────────
def view(
    *,
    ip_suffix: int,
    channels_per_afe: Dict[int, List[int]],
    samples: int = 1000,
    n_wf: int = 10,
    html: str = "waveforms.html",
) -> None:
    """
    Acquire ``n_wf`` wave-forms for each (AFE, channel) entry in
    *channels_per_afe* and write an interactive HTML file.

    • first two rows – individual wave-forms (faint) & their mean ±1 σ band
    • third row      – RMS statistics table
    """
    full_ip = endpoint_ip(ip_suffix)
    dev = Daphne(full_ip)

    afes = sorted(channels_per_afe.keys())
    rows, cols = 3, 3
    subplot_titles = [f"AFE {a}" for a in afes] + ["RMS statistics"]

    fig = make_subplots(
        rows=rows,
        cols=cols,
        subplot_titles=subplot_titles,
        horizontal_spacing=0.05,
        vertical_spacing=0.12,
        specs=[
            [{"type": "xy"}] * cols,
            [{"type": "xy"}] * cols,
            [{"type": "domain", "colspan": 3}, None, None],
        ],
    )

    # one colour per channel (stable across AFEs)
    uniq_ch = sorted({c for chs in channels_per_afe.values() for c in chs})
    colour_map = {ch: col for ch, col in zip(uniq_ch, _colour_cycle(len(uniq_ch)))}

    rms_stats = {}
    dt = 16e-9  # 16 ns / sample

    for idx, afe in enumerate(afes):
        row = 1 if idx < cols else 2
        col = (idx % cols) + 1

        for ch in channels_per_afe[afe]:
            wf_stack = []
            colour = colour_map[ch]

            # ── acquisition ───────────────────────────────────────────────
            for _ in range(n_wf):
                dev.write_reg(0x2020, [1234]); dev.write_reg(0x2021, [1234])
                wf = dev.read_waveform(afe=afe, ch=ch, samples=samples)
                wf_stack.append(wf)

                # Each individual WF (faint)
                t = np.arange(len(wf)) * dt * 1e6  # µs
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

            wf_stack = np.vstack(wf_stack)
            mean_wf, std_wf = wf_stack.mean(axis=0), wf_stack.std(axis=0)
            t = np.arange(len(mean_wf)) * dt * 1e6  # µs

            # ±1 σ band
            fig.add_trace(
                go.Scatter(
                    x=np.concatenate([t, t[::-1]]),
                    y=np.concatenate([mean_wf + std_wf, (mean_wf - std_wf)[::-1]]),
                    mode="lines",
                    line=dict(width=0),
                    fill="toself",
                    fillcolor=_hex_to_rgba(colour, 0.20),
                    hoverinfo="skip",
                    showlegend=False,
                ),
                row=row, col=col,
            )
            # mean WF (thicker)
            fig.add_trace(
                go.Scatter(
                    x=t, y=mean_wf,
                    mode="lines",
                    line=dict(width=1.5, color=colour),
                    name=f"CH {ch}",
                    showlegend=False,         # ← hide legend
                ),
                row=row, col=col,
            )

            rms_stats[f"AFE {afe} CH {ch}"] = round(_rms(wf_stack.ravel()), 2)

    # ── RMS table ──────────────────────────────────────────────────────────
    hdr, cells = zip(*sorted(rms_stats.items(), key=lambda kv: kv[0]))
    fig.add_trace(
        go.Table(
            header=dict(
                values=["Channel", "RMS [mV]"],
                fill_color="lightgrey",
                font=dict(size=13),
                align="left",
            ),
            cells=dict(values=[hdr, cells], align="left", font=dict(size=12)),
        ),
        row=3, col=1,
    )

    # ── layout tweaks ──────────────────────────────────────────────────────
    fig.update_xaxes(title="time [µs]", row=1, col=1)
    fig.update_yaxes(title="ADC counts", row=1, col=1)
    fig.update_layout(
        height=900, width=1300,
        template="simple_white",
        margin=dict(l=65, r=35, t=80, b=55),
        title=dict(
            text=f"DAPHNE wave-forms  –  endpoint {full_ip}",
            x=0.01, xanchor="left",
        ),
    )

    out = Path(html).expanduser().resolve()
    fig.write_html(out, include_mathjax="cdn")
    print(f"🔬  Interactive figure written to {out}")


# ────────────────────── helper to load channels dict from file ──────────────
def _load_channels_dict(path: str) -> Dict[int, List[int]]:
    """Import a ``channels_to_acquire`` dict from an arbitrary *.py* file."""
    p = Path(path).expanduser().resolve()
    spec = importlib.util.spec_from_file_location("ch_cfg", p)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)                # type: ignore[union-attr]
    return getattr(mod, "channels_to_acquire")


# ──────────────────────────── CLI hook ──────────────────────────────────────
if __name__ == "__main__":      # pragma: no cover
    import argparse, importlib.util

    ap = argparse.ArgumentParser(
        description="Plot DAPHNE wave-forms with Plotly",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--ip", required=True, type=int, help="endpoint suffix")
    ap.add_argument("--channels-file", required=True,
                    help="Python file holding a 'channels_to_acquire' dict")
    ap.add_argument("--samples", type=int, default=1000, help="# ADC samples")
    ap.add_argument("-n", "--n_wf", type=int, default=10,
                    help="# wave-forms per (AFE, channel)")
    ap.add_argument("--html", default="waveforms.html", help="output file")

    args = ap.parse_args()

    view(
        ip_suffix=args.ip,
        channels_per_afe=_load_channels_dict(args.channels_file),
        samples=args.samples,
        n_wf=args.n_wf,
        html=args.html,
    )
