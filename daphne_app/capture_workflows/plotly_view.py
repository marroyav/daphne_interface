# daphne_app/capture_workflows/plotly_view.py
"""
Interactive Plotly visualisation of DAPHNE spy-buffer wave-forms
================================================================

Example
-------
daphne capture plotly --details details.json        \\
                      --samples 4000 --n-wf 10      \\
                      --trigger aligned             \\
                      --html wf.html
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Iterable
import itertools
import importlib.util
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import rich

from daphne_app.hardware.daphne import Daphne
from daphne_app.utils.ip_utils import endpoint_ip

# ───────────────────────────── helpers ──────────────────────────────
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


# ───────────────────────────── main view ────────────────────────────
def view(
    *,
    ip_suffix: int,
    channels_per_afe: Dict[int, List[int]],
    samples: int = 1000,
    n_wf: int = 10,
    html: str = "waveforms.html",
    trigger: str = "software",          #  NEW  {software, aligned}
    save_wf: str | None = None,
) -> None:
    """
    Build an interactive Plotly HTML with mean ±1σ envelopes and an RMS table.

    Parameters
    ----------
    trigger
        • **software** – write *once* to 0x2000 before every read
        • **aligned**  – write to 0x2020 *and* 0x2021 (centred buffer)
    save_wf
        Optional path to save a ``np.savez`` file with the raw wave-forms.
    """
    if trigger not in {"software", "aligned"}:
        raise ValueError("trigger must be 'software' or 'aligned'")

    full_ip = endpoint_ip(ip_suffix)
    rich.print(f"[bold]→ connecting {full_ip}[/]")
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
    dt = 16e-9                                               # 16 ns / sample

    # optional raw-waveform store
    wf_store: Dict[str, np.ndarray] = {}

    for idx, afe in enumerate(afes):
        row = 1 if idx < cols else 2
        col = (idx % cols) + 1

        for ch in channels_per_afe[afe]:
            wf_stack = []
            colour = colour_map[ch]

            for _ in range(n_wf):
                # ------------------- trigger --------------------
                if trigger == "software":
                    dev.write_reg(0x2000, [1234])
                else:                                         # aligned
                    dev.write_reg(0x2020, [1234])
                    dev.write_reg(0x2021, [1234])

                wf = dev.read_waveform(afe=afe, ch=ch, samples=samples)
                wf_stack.append(wf)

            wf_arr = np.vstack(wf_stack)
            wf_store[f"AFE{afe}_CH{ch}"] = wf_arr            # save later

            mean_wf = wf_arr.mean(axis=0)
            std_wf  = wf_arr.std(axis=0)
            t = np.arange(len(mean_wf)) * dt * 1e6           # µs

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
            # mean trace
            fig.add_trace(
                go.Scatter(
                    x=t, y=mean_wf,
                    mode="lines",
                    line=dict(width=1.4, color=colour),
                    name=f"CH {ch}",
                    showlegend=False,
                ),
                row=row, col=col,
            )

            rms_stats[f"AFE {afe} CH {ch}"] = round(_rms(wf_arr.ravel()), 2)

    # ─────────────── RMS table ───────────────
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

    # ─────────────── layout ───────────────
    fig.update_xaxes(title="time [µs]", row=1, col=1)
    fig.update_yaxes(title="ADC counts", row=1, col=1)
    fig.update_layout(
        height=900, width=1300,
        template="simple_white",
        margin=dict(l=65, r=35, t=80, b=55),
        title=dict(
            text=f"DAPHNE spy-buffer wave-forms – endpoint {full_ip}",
            x=0.01, xanchor="left",
        ),
    )

    out = Path(html).expanduser().resolve()
    fig.write_html(out, include_mathjax="cdn")
    rich.print(f"[green]🔬  Interactive HTML written to {out}[/]")

    # optional raw save
    if save_wf:
        np.savez_compressed(Path(save_wf).expanduser(), **wf_store)
        rich.print(f"[green]🗄️   Raw wave-forms saved to {save_wf}[/]")


# ──────────────────────────── channels-dict loader ─────────────────────────
def _load_channels_dict(path: str) -> Dict[int, List[int]]:
    """Import a ``channels_to_acquire`` dict from an arbitrary *.py* file."""
    p = Path(path).expanduser().resolve()
    spec = importlib.util.spec_from_file_location("ch_cfg", p)
    mod = importlib.util.module_from_spec(spec)        # type: ignore[arg-type]
    spec.loader.exec_module(mod)                       # type: ignore[union-attr]
    return getattr(mod, "channels_to_acquire")


# ─────────────────────────── CLI hook (python -m …) ────────────────────────
if __name__ == "__main__":          # pragma: no cover
    import argparse

    ap = argparse.ArgumentParser(
        description="Plot DAPHNE spy-buffer wave-forms with Plotly",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    ap.add_argument("--ip", required=True, type=int, help="endpoint suffix")
    ap.add_argument("--channels-file", required=True,
                    help="Python file with `channels_to_acquire` dict")
    ap.add_argument("--samples", type=int, default=1000, help="# ADC samples")
    ap.add_argument("-n", "--n-wf", type=int, default=10,
                    help="# wave-forms per (AFE, channel)")
    ap.add_argument("--html", default="waveforms.html", help="output HTML")
    ap.add_argument("--trigger", choices=["software", "aligned"],
                    default="software", help="trigger mode")
    ap.add_argument("--save-wf", help="optional .npz file for raw data")

    args = ap.parse_args()

    view(
        ip_suffix=args.ip,
        channels_per_afe=_load_channels_dict(args.channels_file),
        samples=args.samples,
        n_wf=args.n_wf,
        html=args.html,
        trigger=args.trigger,
        save_wf=args.save_wf,
    )
