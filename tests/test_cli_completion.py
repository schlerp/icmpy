from __future__ import annotations

from typer.testing import CliRunner

from icmpy.cli import app

runner = CliRunner()


def test_completion_rejects_invalid_shell() -> None:
    result = runner.invoke(app, ["completion", "powershell"])
    assert result.exit_code == 1
    assert "Unsupported shell" in result.output


def test_completion_lists_supported_shells() -> None:
    result = runner.invoke(app, ["completion", "powershell"])
    assert "bash" in result.output
    assert "zsh" in result.output
    assert "fish" in result.output
