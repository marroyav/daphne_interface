"""
Top-level Typer CLI for every-day DAPHNE DAQ tasks
=================================================

$ daphne configure --ip 4,5            # full conf.   (clocks → analog → …)
$ daphne configure analog --ip 7       # only analog offsets / gains
$ daphne configure json cfg.json       # drive everything from JSON

$ daphne check --ip 7                  # full diagnostic suite
$ daphne check counters --ip 4,5       # only the counter spy

$ daphne capture plotly --details details.json -n-wf 50 --html wf.html
"""

from __future__ import annotations
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec
from typing import List, Dict
import json
import ipaddress
import sys

import typer


# ──────────────────────────────────────────────
#  Local imports – adjust paths / names if needed
# ──────────────────────────────────────────────
from daphne_app.utils.settings   import valid_ips
from daphne_app.utils.ip_utils   import ip_suffix, endpoint_ip

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

from daphne_app.config_workflows.self_trigger import (
    _translate_json_kwargs as _st_json_kwargs,
)

from daphne_app.capture_workflows import (
    plotly_view,
    live_plot,
)



# ──────────────────────────────────────────────
#  Typer “sub-apps”
# ──────────────────────────────────────────────
app          = typer.Typer(help="DAPHNE helper CLI",
                           rich_markup_mode="rich", add_completion=False)
config_app   = typer.Typer(help="Board-configuration workflows")
check_app    = typer.Typer(help="One-shot / live sanity checks")
capture_app  = typer.Typer(help="Spy-buffer capture & viewers")
calib_app    = typer.Typer(help="Automated calibrations")

app.add_typer(config_app, name="configure")
app.add_typer(check_app,  name="check")
app.add_typer(capture_app, name="capture")
app.add_typer(calib_app,   name="calibrate")

# ╭───────────────────────────────────────────╮
# │ Helpers                                   │
# ╰───────────────────────────────────────────╯
def _parse_ip_list(ip_arg: str) -> List[int]:
    """
    Convert “4,5,7” or “ALL” into a list of endpoint suffix integers.
    """
    ip_arg = ip_arg.upper()
    if ip_arg == "ALL":
        return valid_ips()

    try:
        ips = [int(x) for x in ip_arg.split(",") if x]
    except ValueError as exc:
        raise typer.BadParameter(
            "IP list must be comma-separated integers or ALL"
        ) from exc

    invalid = [x for x in ips if x not in valid_ips()]
    if invalid:
        raise typer.BadParameter(f"Invalid IP(s): {invalid}. Valid: {valid_ips()}")
    return ips


# ╭───────────────────────────────────────────╮
# │ CONFIGURE                                 │
# ╰───────────────────────────────────────────╯
@config_app.command("clocks")
def conf_clocks(ip: str = typer.Option("ALL", "--ip")):
    """Re-lock and verify the clock-tree."""
    clocks.configure(_parse_ip_list(ip))


@config_app.command("analog")
def conf_analog(
    ip: str = typer.Option("ALL", "--ip"),
    offset: int = typer.Option(2250, "--offset-mv"),
    gain:   int = typer.Option(1,    "--gain"),
):
    """Write PGA gains / offset-DAC values."""
    analog.configure(_parse_ip_list(ip), offset_mv=offset, gain=gain)


@config_app.command("datamodes")
def conf_datamodes(ip: str = typer.Option("ALL", "--ip")):
    """Write data-mode registers (0x3000 / 0x6001)."""
    datamodes.configure(_parse_ip_list(ip))


@config_app.command("trigger")
def conf_trigger(ip: str = typer.Option("ALL", "--ip")):
    """Write full-stream trigger matrices (16×16)."""
    trigger.configure_full_stream(_parse_ip_list(ip))


@config_app.command("self-trigger")
def conf_self_trigger(ip: str = typer.Option("ALL", "--ip")):
    """Program self-trigger filter / masks."""
    self_trigger.configure(_parse_ip_list(ip))


@config_app.command("json", help="Full configuration driven by a JSON file")
def configure_from_json(file: Path):
    """
    Parse *details.json* (or any compatible file) and execute every step
    (clocks → analog → datamode → self-trigger → trigger) for each board.
    """
    import rich

    cfg    = json.loads(file.read_text())
    common = cfg["common_conf"]

    for dev in cfg["devices"]:
        full_ip = str(ipaddress.ip_address(dev["ip"]))
        suf     = ip_suffix(full_ip)

        rich.print(f"[bold]→ Configuring {full_ip}[/]")

        # 1. clocks
        clocks.configure([suf])

        # 2. analog (only listed channels)
        idx   = dev["channels"]["indices"]
        offs  = dev["channels"]["offsets"]
        gains = [common["offset_gain"]] * len(idx)
        analog.configure([suf], offsets=offs, gains=gains, only_indices=idx)

        # 3. data-mode
        datamodes.configure([suf], force_mode=dev["mode"])

        # 4. self-trigger
        if dev.get("self_trigger"):
            self_trigger.configure([suf], **_st_json_kwargs(dev["self_trigger"]))

        # 5. trigger matrix (if board belongs to full-stream set)
        if suf in trigger.full_stream_endpoints():
            trigger.configure_full_stream([suf])

    typer.secho("✅  Configuration finished", fg=typer.colors.GREEN)


# ╭───────────────────────────────────────────╮
# │ CHECK                                     │
# ╰───────────────────────────────────────────╯
@check_app.command("datamodes")
def check_dm(ip: str = typer.Option("ALL", "--ip")):
    """Verify that registers 0x3000 / 0x6001 match expectations."""
    datamodes_check.run(_parse_ip_list(ip))


@check_app.command("endpoints")
def check_endpoints_cmd(ip: str = typer.Option("ALL", "--ip")):
    """Ping & basic I2C ping of every AFE."""
    endpoints.verify(_parse_ip_list(ip))


@check_app.command("timestamp")
def check_ts(ip: str = typer.Option("ALL", "--ip")):
    """Compare timestamp counters across boards."""
    timestamp.check(_parse_ip_list(ip))


@check_app.command("counters")
def check_ct(ip: str = typer.Option("ALL", "--ip")):
    """Spy on the run-time error counters."""
    counters.spy(_parse_ip_list(ip))


@check_app.command("analog")
def check_an(ip: str = typer.Option("ALL", "--ip")):
    """Read back PGA gains / offsets and compare with golden."""
    analog_check.run(_parse_ip_list(ip))


@check_app.command("self-trigger")
def check_st(ip: str = typer.Option("ALL", "--ip")):
    """Dump and decode self-trigger registers."""
    self_trigger_check.check(_parse_ip_list(ip))


@check_app.callback(invoke_without_command=True)
def _check_all(ctx: typer.Context,
               ip: str = typer.Option("ALL", "--ip")):
    """
    *If no sub-command is given* this runs the **full** suite.
    """
    ips = _parse_ip_list(ip)
    if ctx.invoked_subcommand:
        return

    datamodes_check.run(ips)
    endpoints.verify(ips)
    timestamp.check(ips)
    counters.spy(ips)
    analog_check.run(ips)
    self_trigger_check.check(ips)

    typer.echo("✅  All checks finished – inspect output above")


# ╭───────────────────────────────────────────╮
# │ CAPTURE                                   │
# ╰───────────────────────────────────────────╯
# helper – fetch channels from details.json
def _channels_from_json(details: Path) -> tuple[int, Dict[int, List[int]]]:
    data = json.loads(details.read_text())
    dev  = data["devices"][0]          # by convention one board per file
    full_ip = str(ipaddress.ip_address(dev["ip"]))
    mapping: Dict[int, List[int]] = {}
    for idx in dev["channels"]["indices"]:
        afe, ch = divmod(idx, 8)
        mapping.setdefault(afe, []).append(ch)
    for v in mapping.values():
        v.sort()
    return ip_suffix(full_ip), mapping


# helper – import arbitrary python file with `channels_to_acquire`
def _channels_from_py(file: Path) -> Dict[int, List[int]]:
    spec = spec_from_file_location("ch_cfg", file)
    mod  = module_from_spec(spec)            # type: ignore[arg-type]
    spec.loader.exec_module(mod)             # type: ignore[union-attr]
    return getattr(mod, "channels_to_acquire")

# ------------------------------------------------------------------
@capture_app.command("plotly")
def cap_plotly(
    # ----- where to read IP & channels ----------------------------
    details: Path = typer.Option(
        None, "--details", exists=True, readable=True,
        help="details.json containing IP & channel list",
    ),
    channels_file: Path = typer.Option(
        None, "--channels-file", exists=True, readable=True,
        help="Python file exporting `channels_to_acquire`",
    ),
    ip: int = typer.Option(
        None, "--ip",
        help="Endpoint suffix (ignored when --details is used)",
    ),
    # ----- acquisition parameters ---------------------------------
    samples: int = typer.Option(1000, "--samples", help="# ADC samples"),
    n_wf:    int = typer.Option(10,   "--n-wf",    help="# wave-forms / ch"),
    # ----- output --------------------------------------------------
    html: str = typer.Option("waveforms.html", "--html", help="Output HTML"),
    save_wf: str | None = typer.Option(
        None, "--save-wf",
        help="Optional .npz / .npy / .pkl dump of raw wave-forms",
    ),
) -> None:
    """
    Acquire spy-buffer wave-forms and build a polished interactive Plotly
    figure (time-domain traces + RMS summary table).

    Preferred usage is **--details details.json**; alternatively provide
    **--channels-file** *and* **--ip**.
    """
    if details:
        ip_suf, ch_map = _channels_from_json(details)
    else:
        if not (channels_file and ip):
            typer.secho("Need either --details OR (--channels-file AND --ip)",
                        fg=typer.colors.RED)
            raise typer.Exit(code=1)
        ch_map = _channels_from_py(channels_file)
        ip_suf = ip

    plotly_view.view(
        ip_suffix        = ip_suf,
        channels_per_afe = ch_map,
        samples          = samples,
        n_wf             = n_wf,
        html             = html,
        save_wf          = save_wf,
    )


@capture_app.command("live")
def cap_live(
    ip: int  = typer.Option(..., "--ip", help="Endpoint suffix"),
    afe: int = typer.Option(0,  "--afe"),
    ch:  int = typer.Option(0,  "--ch"),
    samples: int = typer.Option(1000, "--samples"),
):
    """Simple matplotlib live-scroll viewer (Qt backend)."""
    live_plot.run(ip, afe, ch, samples)


# ╭───────────────────────────────────────────╮
# │ CALIBRATE – offsets                       │
# ╰───────────────────────────────────────────╯
from daphne_app.calibration import offsets as offsets_calib

@calib_app.command("offsets")
def calib_offsets(
    # where to get channels / IP
    details: Path = typer.Option(None, "--details", exists=True, readable=True,
                                 help="details.json with IP & channel list"),
    channels_file: Path = typer.Option(None, "--channels-file", exists=True, readable=True,
                                       help="Python file with `channels_to_acquire`"),
    ip: int = typer.Option(None, "--ip", help="Endpoint suffix (ignored with --details)"),
    # algo parameters
    target:   int = typer.Option(4000, "--target", help="Target baseline [ADC]"),
    band:     int = typer.Option(2,    "--band",   help="±band counts tolerance"),
    samples:  int = typer.Option(4000, "--samples"),
    n_wf:     int = typer.Option(3,    "--n-wf"),
    max_iter: int = typer.Option(7,    "--max-iters"),
    step_init: int = typer.Option(50,  "--step-init",
                                  help="Initial DAC step [counts]"),
    # outputs
    save_json: Path | None = typer.Option(None, "--save-json",
                                          help="Write final DAC map here (.json)"),
) -> None:
    """
    Calibrate PGA **offset DACs** until every channel baseline lies within
    *±band* ADC counts of *target*.

    Strategy
    --------
    1. Starting DACs are **read from the board** (“RD OFFSET CH <n>”).
       Inversion is taken from the JSON field *“enable_inverter”*.
    2. A binary-shrink loop:
       – first move by *step-init* DAC counts,
       – half the step whenever the sign of the error flips,
       – lock a channel once it enters the target band.
    3. Stops early when all channels are locked or *max_iters* reached.
       A convergence plot and a full log are written automatically.

    Example
    -------
    daphne calibrate offsets --details details.json \\
                             --target 4000 --band 2 \\
                             --step-init 50 --n-wf 3 \\
                             --save-json best_offsets.json
    """
    if details:
        ip_suf, ch_map, inv_set = _channels_from_json(details)
    else:
        if not (channels_file and ip):
            typer.secho("Need either --details OR (--channels-file AND --ip)",
                        fg=typer.colors.RED)
            raise typer.Exit(1)
        ch_map = _channels_from_py(channels_file)
        ip_suf = ip

    offsets_calib.run(
        ip_suffix        = ip_suf,
        channels_per_afe = ch_map,
        inverted_glob    = inv_set if details else set(),
        target           = target,
        band             = band,
        samples          = samples,
        n_wf             = n_wf,
        max_iters        = max_iter,
        step_init        = step_init,
        save_json        = save_json,
    )

# ╭───────────────────────────────────────────╮
# │ Entry-point for  “python -m daphne_app”   │
# ╰───────────────────────────────────────────╯
def main() -> None:
    app()


if __name__ == "__main__":   # pragma: no cover
    main()
