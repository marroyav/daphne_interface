
import typer
from typing import List

# NOTE: update imports to real modules once you implement them
from daphne_app.config_workflows import clocks, analog, datamodes, trigger
from daphne_app.check_workflows import (
    datamodes_check,
    endpoints,
    timestamp,
    counters,
)

app = typer.Typer(help="Unified DAPHNE DAQ controller")

VALID_IPS = [4, 5, 6, 7, 9, 10, 11, 12, 13]


def _parse_ip_list(ip_arg: str) -> List[int]:
    """Parse --ip argument (comma‑separated list or ALL)."""
    ip_arg = ip_arg.upper()
    if ip_arg == "ALL":
        return VALID_IPS
    try:
        ips = [int(x) for x in ip_arg.split(",") if x]
    except ValueError as exc:
        raise typer.BadParameter("IP list must be comma‑separated integers or ALL") from exc

    invalid = [ip for ip in ips if ip not in VALID_IPS]
    if invalid:
        raise typer.BadParameter(f"Invalid IP(s): {invalid}. Valid: {VALID_IPS}")
    return ips


@app.command()
def configure(ip: str = typer.Option("ALL", "--ip", help="Comma‑separated endpoint suffixes")):
    """Run full configuration (equivalent to 00_run_config.py)."""
    ips = _parse_ip_list(ip)
    typer.echo(f"Configuring endpoints: {ips}")
    clocks.configure(ips)
    analog.configure(ips)
    datamodes.configure(ips)
    trigger.configure_full_stream(ips)
    typer.echo("✅  Configuration complete")


@app.command()
def check(ip: str = typer.Option("ALL", "--ip", help="Comma‑separated endpoint suffixes")):
    """Run standard DAQ sanity checks (equivalent to 01_run_checks.py)."""
    ips = _parse_ip_list(ip)
    typer.echo(f"Running checks for endpoints: {ips}")
    datamodes_check.run(ips)
    endpoints.verify(ips)
    timestamp.check(ips)
    counters.spy(ips)
    typer.echo("✅  All checks finished – inspect output above")


@app.command()
def clocks_only(ip: str = typer.Option("ALL", "--ip")):
    """Just (re)configure the timing block."""
    ips = _parse_ip_list(ip)
    clocks.configure(ips)


@app.command()
def datamode(ip: str = typer.Option("ALL", "--ip")):
    """Check current data‑mode register."""
    ips = _parse_ip_list(ip)
    datamodes_check.run(ips)


if __name__ == "__main__":
    app()
