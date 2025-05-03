# daphne_app/cli.py
"""
Top-level CLI for every-day DAPHNE DAQ tasks
===========================================

Examples
--------
$ daphne configure --ip 4,5
$ daphne configure bias   --ip 7 --mv 4095 --dac 700,700,800,800,800
$ daphne configure json   np02_details.json
$ daphne check            --ip 7
"""

from __future__ import annotations

# ───────────────────────── stdlib ─────────────────────────
import ipaddress
import json
import logging.config
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Dict, List

# ───────────────────────── 3rd-party ──────────────────────
import importlib.resources as pkg
import rich
import typer
import yaml

# ───────────────────────── local ──────────────────────────
from daphne_app.utils.ip_utils import endpoint_ip, ip_suffix
from daphne_app.utils.settings import valid_ips

# logging --------------------------------------------------
with pkg.files("daphne_app").joinpath("logging.yaml").open("rb") as fh:
    logging.config.dictConfig(yaml.safe_load(fh))

from daphne_app.config_workflows import (
    analog,
    bias as bias_conf,
    clocks,
    datamodes,
    self_trigger,
    trigger,
)
from daphne_app.check_workflows import (
    analog_check,
    counters,
    datamodes_check,
    endpoints,
    self_trigger as self_trigger_check,
    timestamp,
)
from daphne_app.calibration import offsets as offsets_calib
from daphne_app.capture_workflows import live_plot, plotly_view
from daphne_app.config_workflows.self_trigger import _translate_json_kwargs

# ╭──────────────────────── typer sub-apps ───────────────────────╮
app = typer.Typer(help="DAPHNE helper CLI")
config_app = typer.Typer(help="Board-configuration workflows")
check_app = typer.Typer(help="One-shot / live sanity checks")
capture_app = typer.Typer(help="Spy-buffer capture & viewers")
calib_app = typer.Typer(help="Calibration utilities")

app.add_typer(config_app, name="configure")
app.add_typer(check_app, name="check")
app.add_typer(capture_app, name="capture")
app.add_typer(calib_app, name="calibrate")

# ╭──────────────────────── helpers ──────────────────────────────╮
def _parse_ip_list(arg: str) -> List[int]:
    if arg.upper() == "ALL":
        return valid_ips()
    try:
        ips = [int(x) for x in arg.split(",") if x]
    except ValueError as exc:
        raise typer.BadParameter(
            "IP list must be comma-separated integers or ALL"
        ) from exc

    bad = [x for x in ips if x not in valid_ips()]
    if bad:
        raise typer.BadParameter(f"Invalid IP(s): {bad}. Valid: {valid_ips()}")
    return ips


# ╭────────────────────── configure commands ─────────────────────╮
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


@config_app.command("bias")
@config_app.command("bias")
def conf_bias(
    ip: str = typer.Option("ALL", "--ip"),
    mv: int = typer.Option(700, "--mv",  help="VBIASCTRL in mV"),
    bias_set: str | None = typer.Option(        # ← rename here
        None,
        "--set",
        help="5 comma-sep DAC counts for BIASSET AFE0-4 "
             "(e.g. 700,700,800,800,800)",
    ),
) -> None:
    """Write VBIASCTRL **and** optional BIASSET per-AFE DACs."""
    # ── parse comma list -------------------------------------------------
    dac_vals: list[int] | None = None
    if bias_set:
        try:
            parts = [int(x) for x in bias_set.split(",")]
            if len(parts) != 5:
                raise ValueError
            dac_vals = parts
        except ValueError:
            typer.secho("⚠  --set needs exactly 5 integers (AFE0-4)", fg=typer.colors.RED)
            raise typer.Exit(1)

    bias_conf.configure_bias(
        _parse_ip_list(ip),
        vbias_mv=mv,
        bias_set=dac_vals,          # ← pass to workflow
    )

@config_app.command("trim")
def conf_trim(
    ip: str = typer.Option(..., "--ip"),
    file: Path = typer.Option(
        ...,
        "--file",
        exists=True,
        readable=True,
        help="JSON with {channel: value} map",
    ),
):
    trim_map = json.loads(file.read_text())
    bias_conf.configure_trim(_parse_ip_list(ip), trim_map=trim_map)


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
    cfg = json.loads(file.read_text())
    common = cfg["common_conf"]

    for dev in cfg["devices"]:
        full_ip = str(ipaddress.ip_address(dev["ip"]))
        suf = ip_suffix(full_ip)

        rich.print(f"[bold]→ Configuring {full_ip}[/]")

        # 1. clocks
        clocks.configure([suf])

        # 2. analog chain
        ch_idx = dev["channels"]["indices"]
        offs = dev["channels"]["offsets"]
        gains = [common["offset_gain"]] * len(ch_idx)
        vg = dev["channels"].get("attenuators")
        analog.configure(
            [suf],
            offsets=offs,
            gains=gains,
            only_indices=ch_idx,
            attenuators=vg,
        )

        # 3. mode registers
        datamodes.configure([suf], force_mode=dev["mode"])

        # 4. self-trigger
        if dev.get("self_trigger"):
            self_trigger.configure(
                [suf], **_translate_json_kwargs(dev["self_trigger"])
            )

        # 5. trigger matrix for full-stream boards
        if suf in trigger.full_stream_endpoints():
            trigger.configure_full_stream([suf])

    typer.secho("✅  Configuration finished", fg=typer.colors.GREEN)


# ╭──────────────────────── check commands ────────────────────────╮
@check_app.command("datamodes")
def check_dm(ip: str = typer.Option("ALL", "--ip")):
    datamodes_check.run(_parse_ip_list(ip))


@check_app.command("endpoints")
def check_endpoints_cmd(ip: str = typer.Option("ALL", "--ip")):
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


@check_app.command("bias")
def check_bias(ip: str = typer.Option("ALL", "--ip")):
    bias_conf.check_bias(_parse_ip_list(ip))


@check_app.command("trim")
def check_trim(ip: str = typer.Option("ALL", "--ip")):
    bias_conf.check_trim(_parse_ip_list(ip))


@check_app.command("self-trigger")
def check_st(ip: str = typer.Option("ALL", "--ip")):
    self_trigger_check.check(_parse_ip_list(ip))


@check_app.callback(invoke_without_command=True)
def _check_all(ctx: typer.Context, ip: str = typer.Option("ALL", "--ip")):
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


# ╭───────────────────── capture helpers / CLI ────────────────────╮
def _channels_from_json(details: Path) -> tuple[int, Dict[int, List[int]]]:
    data = json.loads(details.read_text())
    dev = data["devices"][0]
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
    mod = module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return getattr(mod, "channels_to_acquire")


@capture_app.command("plotly")
def cap_plotly(
    details: Path = typer.Option(
        None, "--details", exists=True, readable=True, help="details.json"
    ),
    channels_file: Path = typer.Option(
        None,
        "--channels-file",
        exists=True,
        readable=True,
        help="Python file with `channels_to_acquire`",
    ),
    ip: int = typer.Option(None, "--ip", help="Endpoint suffix"),
    samples: int = typer.Option(1000, "--samples"),
    n_wf: int = typer.Option(10, "--n-wf"),
    trigger: str = typer.Option("software", "--trigger"),
    html: str = typer.Option("waveforms.html", "--html"),
    save_wf: str | None = typer.Option(None, "--save-wf"),
):
    if details:
        ip_suf, ch_map = _channels_from_json(details)
    else:
        if not (channels_file and ip):
            typer.secho(
                "Need --details OR (--channels-file AND --ip)",
                fg=typer.colors.RED,
            )
            raise typer.Exit(1)
        ch_map = _channels_from_py(channels_file)
        ip_suf = ip

    plotly_view.view(
        ip_suffix=ip_suf,
        channels_per_afe=ch_map,
        samples=samples,
        n_wf=n_wf,
        trigger=trigger,
        html=html,
        save_wf=save_wf,
    )


@capture_app.command("live")
def cap_live(
    ip: int = typer.Option(..., "--ip"),
    afe: int = typer.Option(0, "--afe"),
    ch: int = typer.Option(0, "--ch"),
    samples: int = typer.Option(1000, "--samples"),
):
    live_plot.run(ip, afe, ch, samples)


# ╭────────────────────── calibration CLI ─────────────────────────╮
@calib_app.command("offsets")
def calib_offsets(
    details: Path = typer.Option(None, "--details", exists=True, readable=True),
    channels_file: Path = typer.Option(
        None, "--channels-file", exists=True, readable=True
    ),
    ip: int = typer.Option(None, "--ip"),
    target: int = typer.Option(4000, "--target"),
    band: int = typer.Option(2, "--band"),
    samples: int = typer.Option(4000, "--samples"),
    n_wf: int = typer.Option(3, "--n-wf"),
    max_iter: int = typer.Option(7, "--max-iters"),
    step_init: int = typer.Option(50, "--step-init"),
    step_min: int = typer.Option(4, "--step-min"),
    save_json: Path | None = typer.Option(None, "--save-json"),
):
    if details:
        full_ip, ch_map, inv_set = offsets_calib.channels_from_json(details)
    else:
        if not (channels_file and ip):
            typer.secho(
                "Need --details OR (--channels-file AND --ip)",
                fg=typer.colors.RED,
            )
            raise typer.Exit(1)
        ch_map, inv_set = offsets_calib.channels_from_py(channels_file)
        full_ip = endpoint_ip(ip)

    offsets_calib.run(
        full_ip=full_ip,
        channels_per_afe=ch_map,
        inverted_glob=inv_set,
        target=target,
        band=band,
        samples=samples,
        n_wf=n_wf,
        max_iters=max_iter,
        step_init=step_init,
        step_min=step_min,
        save_json=save_json,
    )


# ╭──────────────────────── module entry-point ────────────────────╮
def main() -> None:
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
