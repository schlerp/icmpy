from __future__ import annotations

from typer.testing import CliRunner

from icmpy.cli import app

runner = CliRunner()


def test_cli_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_cli_help_shows_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "init" in result.output
    assert "validate" in result.output
    assert "build" in result.output
    assert "stage" in result.output


def test_stage_subcommand_help() -> None:
    result = runner.invoke(app, ["stage", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "run" in result.output
