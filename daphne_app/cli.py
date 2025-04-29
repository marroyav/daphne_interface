from __future__ import annotations

"""
daphne_app.cli
==============

Top-level Typer CLI for every‐day DAPHNE DAQ tasks.

$ daphne configure --ip 4,5               # full configuration (clocks → analog → …)
$ daphne configure analog --ip 7          # only analog offsets/gains
$ daphne configure json my_cfg.json       # drive everything from a JSON file

$ daphne check --ip 7                     # run the full suite of checks
$ daphne check counters --ip 4,5          # only the counter spy

$ daphne capture plotly --ip 7            # interactive Plotly spy-buffer viewer
"""

from pathlib import Path
from typing import List

import typer

# ───────────────────────────────────────────
# Local imports
# ───────────────────────────────────────────
from daphne_app.config_workflows import (
    clocks,
    analog,
    datamodes,
    trigger,
    self_trigger,
)
from daphne_app.check_workflows import (
    datamodes_check,
    endpoints,
    timestamp,
    counters,
    analog_check,
    self_trigger as self_trigger_check,
)
from daphne_app.config_workflows.self_trigger import _translate_json_kwargs
from daphne_app.capture_workflows import plotly_view, live_plot
from daphne_app.utils.settings import valid_ips
from daphne_app.utils.ip_utils import ip_suffix

# ───────────────────────────────────────────
# Typer “sub-apps”
# ───────────────────────────────────────────
app = typer.Typer(help="DAPHNE helper CLI")

config_app = typer.Typer(help="Configuration workflow")
check_app = typer.Typer(help="Run-once or live checks")
capture_app = typer.Typer(help="Spy-buffer waveform capture / viewers")

app.add_typer(config_app, name="configure")
app.add_typer(check_app, name="check")
app.add_typer(capture_app, name="capture")


# ╭─────────────────────────────────────────╮
# │ Helper                                                                      │
# ╰─────────────────────────────────────────╯
def _parse_ip_list(ip_arg: str) -> List[int]:
    """
    Convert “4,5,7” or “ALL” into a list of endpoint suffix integers.
    """
    ip_arg = ip_arg.upper()
    if ip_arg == "ALL":
        return valid_ips()

    try:
        ips = [int(x) for x in ip_arg.split(",")]
    except ValueError as exc:
        raise typer.BadParameter("IP list must be comma-separated integers or ALL") from exc

    invalid = [x for x in ips if x not in valid_ips()]
    if invalid:
        raise typer.BadParameter(f"Invalid IP(s): {invalid}. Valid: {valid_ips()}")
    return ips


# ╭─────────────────────────────────────────╮
# │ configure – one step per command        │
# ╰─────────────────────────────────────────╯
@config_app.command("clocks")
def conf_clocks(ip: str = typer.Option("ALL", "--ip")):
    clocks.configure(_parse_ip_list(ip))


@config_app.command("analog")
def conf_analog(
    ip: str = typer.Option("ALL", "--ip"),
    offset: int = typer.Option(2250, "--offset-mv"),
    gain: int = typer.Option(1, "--gain"),
):
    analog.configure(_parse_ip_list(ip), offset_mv=offset, gain=gain)


@config_app.command("datamodes")
def conf_datamodes(ip: str = typer.Option("ALL", "--ip")):
    datamodes.configure(_parse_ip_list(ip))


@config_app.command("trigger")
def conf_trigger(ip: str = typer.Option("ALL", "--ip")):
    trigger.configure_full_stream(_parse_ip_list(ip))


@config_app.command("self-trigger")
def conf_self_trigger(ip: str = typer.Option("ALL", "--ip")):
    self_trigger.configure(_parse_ip_list(ip))


@config_app.command("json", help="Full configuration driven by a JSON file")
def configure_from_json(file: Path):
    """
    Parse the given configuration JSON and execute all steps (clocks, analog,
    datamode, self-trigger …) for every listed device.
    """
    import json, rich

    cfg = json.loads(file.read_text())
    common = cfg["common_conf"]

    for dev in cfg["devices"]:
        full_ip = dev["ip"]
        suffix = ip_suffix(full_ip)

        rich.print(f"[bold]→ Configuring {full_ip}[/]")

        # 1. clocks & timing
        clocks.configure([suffix])

        # 2. analog offsets  (only the channels listed in JSON)
        chan_idx  = dev["channels"]["indices"]          # [0, 7, 8, …]
        chan_off  = dev["channels"]["offsets"]          # len == len(chan_idx)
        gains = [common["offset_gain"]] * len(chan_idx)
        analog.configure([suffix], offsets=chan_off, gains=gains, only_indices=chan_idx,)

        # 3. datamode
        datamodes.configure([suffix], force_mode=dev["mode"])

        # 4. self-trigger (if present)
        if "self_trigger" in dev:
            self_trigger.configure([suffix],
                **_translate_json_kwargs(dev["self_trigger"])
                )

        # 5. optional full-stream trigger map
        if suffix in trigger.full_stream_endpoints():
            trigger.configure_full_stream([suffix])

        rich.print("[green]✅  finished[/]")


# ╭─────────────────────────────────────────╮
# │ check sub-commands                      │
# ╰─────────────────────────────────────────╯
@check_app.command("datamodes")
def check_dm(ip: str = typer.Option("ALL", "--ip")):
    datamodes_check.run(_parse_ip_list(ip))


@check_app.command("endpoints")
def check_endpoints(ip: str = typer.Option("ALL", "--ip")):
    endpoints.verify(_parse_ip_list(ip))


@check_app.command("timestamp")
def check_ts(ip: str = typer.Option("ALL", "--ip")):
    timestamp.check(_parse_ip_list(ip))


@check_app.command("counters")
def check_ct(ip: str = typer.Option("ALL", "--ip")):
    counters.spy(_parse_ip_list(ip))


@check_app.command("analog")
def check_an(ip: str = typer.Option("ALL", "--ip")):
    analog_check.run(_parse_ip_list(ip))


@check_app.command("self-trigger")
def check_st(ip: str = typer.Option("ALL", "--ip")):
    self_trigger_check.check(_parse_ip_list(ip))


@check_app.callback(invoke_without_command=True)
def _check_all(ctx: typer.Context, ip: str = typer.Option("ALL", "--ip")):
    """Run *all* checks if no sub-command was given."""
    ips = _parse_ip_list(ip)
    if ctx.invoked_subcommand is not None:
        return
    datamodes_check.run(ips)
    endpoints.verify(ips)
    timestamp.check(ips)
    counters.spy(ips)
    analog_check.run(ips)
    typer.echo("✅  All checks finished – inspect output above")


# ╭─────────────────────────────────────────╮
# │ capture                                 │
# ╰─────────────────────────────────────────╯
@capture_app.command("plotly")
def cap_plotly(
    ip: str = typer.Option(..., "--ip", help="Endpoint suffix (‘7’ → 10.73.137.107)"),
    afes: str = typer.Option("0,1,2,3,4", "--afes", help="Comma list of AFEs"),
    channels: str = typer.Option("0,7", "--channels", help="Comma list of channels"),
    samples: int = typer.Option(1000, "--samples", help="Samples per waveform"),
    n: int = typer.Option(10, "--n", help="Waveforms per channel"),
    html: str | None = typer.Option(None, "--html", help="Optional HTML export"),
):
    """Interactive Plotly spy-buffer viewer."""
    afes_list = [int(x) for x in afes.split(",") if x]
    chan_list = [int(x) for x in channels.split(",") if x]

    plotly_view.view(
        ip_suffix=int(ip),
        afes=afes_list,
        channels=chan_list,
        samples=samples,
        n_wf=n,
        html_path=Path(html) if html else None,
    )


@capture_app.command("live")
def cap_live(
    ip: str = typer.Option(..., "--ip"),
    afe: int = typer.Option(0, "--afe"),
    channel: int = typer.Option(0, "--ch"),
    samples: int = typer.Option(1000, "--samples"),
):
    """Simple matplotlib live-scroll viewer (Qt backend)."""
    live_plot.run(int(ip), afe, channel, samples)


# ╭─────────────────────────────────────────╮
# │ Entry-point for “python -m daphne_app”  │
# ╰─────────────────────────────────────────╯
def main():
    app()


if __name__ == "__main__":
    main()
