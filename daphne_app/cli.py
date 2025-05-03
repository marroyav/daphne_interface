# daphne_app/cli.py
"""
Top-level CLI for every-day DAPHNE DAQ tasks
===========================================

$ daphne configure --ip 4,5                 # full config (clocks → analog → …)
$ daphne configure bias   --ip 7 --mv 700   # write VBIASCTRL
$ daphne configure trim   --ip 7 --file trim.json
$ daphne configure json   cfg.json          # drive everything from JSON

$ daphne check                --ip 7        # full diagnostic suite
$ daphne check bias           --ip 4,5      # read back VBIAS / POWER / TEMP
$ daphne check trim           --ip 7

$ daphne calibrate offsets    --details details.json …
$ daphne capture  plotly      --details details.json …
"""

from __future__ import annotations

# ────────────────────────────────────────────────────────────────────────────
#  Standard lib
# ────────────────────────────────────────────────────────────────────────────
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec
from typing import List, Dict
import json
import ipaddress
import sys

# ────────────────────────────────────────────────────────────────────────────
#  3rd-party
# ────────────────────────────────────────────────────────────────────────────
import typer
import rich

# ────────────────────────────────────────────────────────────────────────────
#  Local imports    (all grouped here → Typer completion works reliably)
# ────────────────────────────────────────────────────────────────────────────
from daphne_app.utils.settings   import valid_ips
from daphne_app.utils.ip_utils   import ip_suffix, endpoint_ip


import logging.config, yaml, importlib.resources as pkg

# ------------------------------------------------------------------
#  Logging config (daphne_app/logging.yaml)
# ------------------------------------------------------------------
with pkg.files("daphne_app").joinpath("logging.yaml").open("rb") as fh:
    logging.config.dictConfig(yaml.safe_load(fh))


from daphne_app.config_workflows import (
    clocks,
    analog,
    datamodes,
    trigger,
    self_trigger,
    bias       as bias_conf,        # NEW
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
from daphne_app.calibration import offsets as offsets_calib
from daphne_app.capture_workflows import plotly_view, live_plot

# ────────────────────────────────────────────────────────────────────────────
#  Typer “sub-apps”
# ────────────────────────────────────────────────────────────────────────────
app          = typer.Typer(help="DAPHNE helper CLI")          # add_completion=True by default
config_app   = typer.Typer(help="Board-configuration workflows")
check_app    = typer.Typer(help="One-shot / live sanity checks")
capture_app  = typer.Typer(help="Spy-buffer capture & viewers")
calib_app    = typer.Typer(help="Calibration utilities")

app.add_typer(config_app, name="configure")
app.add_typer(check_app,  name="check")
app.add_typer(capture_app,name="capture")
app.add_typer(calib_app,  name="calibrate")

# ╭──────────────────────────────────────────────────────────────────────────╮
# │ Helper                                                                  │
# ╰──────────────────────────────────────────────────────────────────────────╯
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
        raise typer.BadParameter("IP list must be comma-separated integers or ALL") from exc

    invalid = [x for x in ips if x not in valid_ips()]
    if invalid:
        raise typer.BadParameter(f"Invalid IP(s): {invalid}. Valid: {valid_ips()}")
    return ips

# ╭──────────────────────────────────────────────────────────────────────────╮
# │ CONFIGURE                                                               │
# ╰──────────────────────────────────────────────────────────────────────────╯
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


@config_app.command("bias")
def conf_bias(
    ip: str = typer.Option("ALL", "--ip"),
    mv: int = typer.Option(700, "--mv", help="VBIASCTRL in mV"),
):
    """Write *VBIASCTRL* (same value to every AFE)."""
    bias_conf.configure_bias(_parse_ip_list(ip), vbias_mv=mv)


@config_app.command("trim")
def conf_trim(
    ip: str = typer.Option(..., "--ip"),
    file: Path = typer.Option(..., "--file", exists=True, readable=True,
                              help="JSON with {channel: value} map"),
):
    """
    Write TRIM DACs from a JSON file.

    The file must contain a flat dict where keys are *global* channels 0-39,
    values are integer DAC counts 0-4095.
    """
    trim_map = json.loads(file.read_text())
    bias_conf.configure_trim(_parse_ip_list(ip), trim_map=trim_map)


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
    cfg    = json.loads(file.read_text())
    common = cfg["common_conf"]

    for dev in cfg["devices"]:
        full_ip = str(ipaddress.ip_address(dev["ip"]))
        suf     = ip_suffix(full_ip)

        rich.print(f"[bold]→ Configuring {full_ip}[/]")

        clocks.configure([suf])                            # 1
        idx   = dev["channels"]["indices"]                 # 2
        offs  = dev["channels"]["offsets"]
        gains = [common["offset_gain"]] * len(idx)
        analog.configure([suf], offsets=offs, gains=gains, only_indices=idx)
        datamodes.configure([suf], force_mode=dev["mode"]) # 3
        if dev.get("self_trigger"):                        # 4
            self_trigger.configure(
                [suf],
                **_st_json_kwargs(dev["self_trigger"]),)
              # **self_trigger.translate_json_kwargs(dev["self_trigger"]))
        if suf in trigger.full_stream_endpoints():         # 5
            trigger.configure_full_stream([suf])

    typer.secho("✅  Configuration finished", fg=typer.colors.GREEN)

# ╭──────────────────────────────────────────────────────────────────────────╮
# │ CHECK                                                                   │
# ╰──────────────────────────────────────────────────────────────────────────╯
@check_app.command("datamodes")
def check_dm(ip: str = typer.Option("ALL", "--ip")):
    """Verify registers 0x3000 / 0x6001."""
    datamodes_check.run(_parse_ip_list(ip))


@check_app.command("endpoints")
def check_endpoints_cmd(ip: str = typer.Option("ALL", "--ip")):
    """Ping & I²C ping every AFE."""
    endpoints.verify(_parse_ip_list(ip))


@check_app.command("timestamp")
def check_ts(ip: str = typer.Option("ALL", "--ip")):
    """Compare timestamp counters across boards."""
    timestamp.check(_parse_ip_list(ip))


@check_app.command("counters")
def check_ct(ip: str = typer.Option("ALL", "--ip")):
    """Spy on run-time error counters."""
    counters.spy(_parse_ip_list(ip))


@check_app.command("analog")
def check_an(ip: str = typer.Option("ALL", "--ip")):
    """Read back PGA gains / offsets and compare with golden."""
    analog_check.run(_parse_ip_list(ip))


@check_app.command("bias")
def check_bias(ip: str = typer.Option("ALL", "--ip")):
    """Read back VBIAS, POWER, TEMP."""
    bias_conf.check_bias(_parse_ip_list(ip))


@check_app.command("trim")
def check_trim(ip: str = typer.Option("ALL", "--ip")):
    """Dump TRIM registers."""
    bias_conf.check_trim(_parse_ip_list(ip))


@check_app.command("self-trigger")
def check_st(ip: str = typer.Option("ALL", "--ip")):
    """Dump & decode self-trigger registers."""
    self_trigger_check.check(_parse_ip_list(ip))


@check_app.callback(invoke_without_command=True)
def _check_all(ctx: typer.Context, ip: str = typer.Option("ALL", "--ip")):
    """
    If no sub-command is given, run the **full** suite.
    """
    ips = _parse_ip_list(ip)
    if ctx.invoked_subcommand:
        return
    datamodes_check.run(ips)
    endpoints.verify(ips)
    timestamp.check(ips)
    counters.spy(ips)
    analog_check.run(ips)
    bias_conf.check_bias(ips)
    bias_conf.check_trim(ips)
    self_trigger_check.check(ips)
    typer.echo("✅  All checks finished – inspect output above")

# ╭──────────────────────────────────────────────────────────────────────────╮
# │ CAPTURE                                                                 │
# ╰──────────────────────────────────────────────────────────────────────────╯
def _channels_from_json(details: Path) -> tuple[int, Dict[int, List[int]]]:
    data = json.loads(details.read_text())
    dev  = data["devices"][0]
    full_ip = str(ipaddress.ip_address(dev["ip"]))
    mapping: Dict[int, List[int]] = {}
    for idx in dev["channels"]["indices"]:
        afe, ch = divmod(idx, 8)
        mapping.setdefault(afe, []).append(ch)
    for v in mapping.values():
        v.sort()
    return ip_suffix(full_ip), mapping


def _channels_from_py(file: Path) -> Dict[int, List[int]]:
    spec = spec_from_file_location("ch_cfg", file)
    mod  = module_from_spec(spec)                     # type: ignore[arg-type]
    spec.loader.exec_module(mod)                      # type: ignore[union-attr]
    return getattr(mod, "channels_to_acquire")


@capture_app.command("plotly")
def cap_plotly(
    details: Path = typer.Option(
        None, "--details", exists=True, readable=True,
        help="details.json with IP & channel list",
    ),
    channels_file: Path = typer.Option(
        None, "--channels-file", exists=True, readable=True,
        help="Python file exporting `channels_to_acquire`",
    ),
    ip: int = typer.Option(
        None, "--ip", help="Endpoint suffix (ignored with --details)",
    ),
    samples: int = typer.Option(1000, "--samples"),
    n_wf:    int = typer.Option(10,   "--n-wf"),
    trigger: str = typer.Option("software", "--trigger",
                                help="'software' or 'aligned'"),
    html: str = typer.Option("waveforms.html", "--html"),
    save_wf: str | None = typer.Option(None, "--save-wf",
                                       help="optional .npz raw dump"),
) -> None:
    """Interactive Plotly viewer of spy-buffer wave-forms."""
    if details:
        ip_suf, ch_map = _channels_from_json(details)
    else:
        if not (channels_file and ip):
            typer.secho("Need --details OR (--channels-file AND --ip)",
                         fg=typer.colors.RED)
            raise typer.Exit(1)
        ch_map = _channels_from_py(channels_file)
        ip_suf = ip

    plotly_view.view(
        ip_suffix        = ip_suf,
        channels_per_afe = ch_map,
        samples          = samples,
        n_wf             = n_wf,
        trigger          = trigger,
        html             = html,
        save_wf          = save_wf,
    )


@capture_app.command("live")
def cap_live(
    ip: int  = typer.Option(..., "--ip"),
    afe: int = typer.Option(0,   "--afe"),
    ch:  int = typer.Option(0,   "--ch"),
    samples: int = typer.Option(1000, "--samples"),
):
    """Simple matplotlib live-scroll viewer (Qt backend)."""
    live_plot.run(ip, afe, ch, samples)

# ╭──────────────────────────────────────────────────────────────────────────╮
# │ CALIBRATE – offsets                                                     │
# ╰──────────────────────────────────────────────────────────────────────────╯
@calib_app.command("offsets")
def calib_offsets(
    details: Path = typer.Option(None, "--details", exists=True, readable=True),
    channels_file: Path = typer.Option(None, "--channels-file", exists=True, readable=True),
    ip: int = typer.Option(None, "--ip"),
    target:   int = typer.Option(4000, "--target"),
    band:     int = typer.Option(2,    "--band"),
    samples:  int = typer.Option(4000, "--samples"),
    n_wf:     int = typer.Option(3,    "--n-wf"),
    max_iter: int = typer.Option(7,    "--max-iters"),
    step_init:int = typer.Option(50,   "--step-init"),
    step_min :int = typer.Option(4,   "--step-min"),
    save_json: Path | None = typer.Option(None, "--save-json"),
) -> None:
    """
    Calibrate PGA *offset DACs* until every channel baseline lies within
    *±band* ADC counts of *target*.
    """
    if details:
        full_ip, ch_map, inv_set = offsets_calib.channels_from_json(details)
    else:
        if not (channels_file and ip):
            typer.secho("Need --details OR (--channels-file AND --ip)",
                        fg=typer.colors.RED)
            raise typer.Exit(1)
        ch_map, inv_set = offsets_calib.channels_from_py(channels_file)
        ip_suf = ip

    offsets_calib.run(
        full_ip          = full_ip,
        channels_per_afe = ch_map,
        inverted_glob    = inv_set,
        target           = target,
        band             = band,
        samples          = samples,
        n_wf             = n_wf,
        max_iters        = max_iter,
        step_init        = step_init,
        step_min         = step_min,
        save_json        = save_json,
    )

# ╭──────────────────────────────────────────────────────────────────────────╮
# │ Entry-point for  “python -m daphne_app”                                  │
# ╰──────────────────────────────────────────────────────────────────────────╯
def main() -> None:
    app()

if __name__ == "__main__":     # pragma: no cover
    main()
