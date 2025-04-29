from __future__ import annotations
"""
Plotly multi-AFE waveform viewer (interactive).

Invoked from the CLI – see cli.py integration below.
"""

from pathlib import Path
from typing import Sequence, Dict, List
import numpy as np
from rich.console import Console
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..hardware.daphne import Daphne
from ..utils.colors import RED

console = Console()

# ------------- helpers -------------------------------------------------


def _endpoint_ip(suffix: int) -> str:
    return f"10.73.137.{100 + suffix}"


def _capture_all(
    ip_suffix: int,
    afes: Sequence[int],
    channels_dict: Dict[int, Sequence[int]],
    samples: int,
    n_wf: int,
) -> Dict[int, Dict[int, np.ndarray]]:
    """
    Returns nested dict {afe: {ch: np.ndarray[n_wf, samples]}}
    """
    ip = _endpoint_ip(ip_suffix)
    dev = Daphne(ip)
    base = 0x40000000
    step_a = 0x100000
    step_c = 0x10000

    console.print(f"[cyan]Capturing from {ip}[/]")

    all_data: Dict[int, Dict[int, np.ndarray]] = {}
    for afe in afes:
        chs = channels_dict[afe]
        buf: Dict[int, List[np.ndarray]] = {ch: [] for ch in chs}

        for _ in range(n_wf):
            dev.write_reg(0x2020, [1234])   # start spy-buffer
            dev.write_reg(0x2021, [1234])   # latch
            for ch in chs:
                addr = base + step_a * afe + step_c * ch
                raw = dev.read_reg(addr, 50)      # 50 words per call
                wf = np.array(raw[2:], dtype=np.uint16)
                buf[ch].append(wf)

        # stack & store
        all_data[afe] = {ch: np.vstack(buf[ch]) for ch in chs}

    dev.close()
    return all_data


def _plot(
    data: Dict[int, Dict[int, np.ndarray]],
    samples: int,
    html_path: Path | None,
) -> None:
    time_axis = np.linspace(0, samples * 16e-9, samples)

    afes = list(data.keys())
    n_sub = len(afes)
    rows = (n_sub + 2) // 3
    cols = min(n_sub, 3)

    fig = make_subplots(
        rows=rows, cols=cols,
        subplot_titles=[f"AFE {a}" for a in afes],
        vertical_spacing=0.13, horizontal_spacing=0.08,
    )

    subplot_idx = 0
    colors = ['blue', 'orange', 'green', 'red',
          'purple', 'brown', 'gray', 'olive']
#  ──or──  px.colors.qualitative.Plotly

    for afe in afes:
        row = subplot_idx // cols + 1
        col = subplot_idx % cols + 1
        for color_idx, (ch, wfs) in enumerate(data[afe].items()):
            for wf in wfs:
                fig.add_trace(
                    go.Scatter(
                        x=time_axis, y=wf,
                        mode="lines", showlegend=False,
                        line=dict(width=1, color=colors[color_idx % len(colors)]),
                    ),
                    row=row, col=col,
                )
            # add one legend entry per channel
            fig.add_trace(
                go.Scatter(
                    x=[None], y=[None], name=f"CH {ch}",
                    mode="lines",
                    line=dict(color=colors[color_idx % len(colors)]),
                ), row=row, col=col,
            )
        subplot_idx += 1

    # axis labels
    for c in range(1, cols + 1):
        fig.update_xaxes(title_text="Time (s)", row=rows, col=c)
    for r in range(1, rows + 1):
        fig.update_yaxes(title_text="ADC", row=r, col=1)

    fig.update_layout(
        height=400 * rows,
        width=1200,
        title="Waveforms from Daphne",
        legend_title="Channels",
    )
    if html_path:
        fig.write_html(html_path)
        console.print(f"[green]HTML exported → {html_path}[/]")
    fig.show()


# ------------- public entry -------------------------------------------


def view(
    ip_suffix: int,
    afes: Sequence[int],
    channels: Sequence[int],
    samples: int,
    n_wf: int,
    html_path: Path | None,
) -> None:
    """
    Capture & plot waveforms.

    channels is interpreted as the *same* list for every AFE.
    """
    ch_dict = {afe: channels for afe in afes}
    try:
        data = _capture_all(ip_suffix, afes, ch_dict, samples, n_wf)
        _plot(data, samples, html_path)
    except Exception as exc:                      # noqa: BLE001
        console.print(f"[{RED}]Error: {exc}[/]")
