# tests/test_cli_basic.py
from typer.testing import CliRunner
from daphne_app.cli import app   # Typer app

runner = CliRunner()

def test_help_runs():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.stdout
