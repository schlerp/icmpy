from __future__ import annotations

from typer.testing import CliRunner

from icmpy.cli import app

runner = CliRunner()


def test_build_without_template_shows_table() -> None:
    result = runner.invoke(app, ["build"])
    assert result.exit_code == 1
    assert "Available built-in templates" in result.output
    # spot check a few templates appear in the table
    assert "script-to-animation" in result.output
    assert "long-form-essay" in result.output
    assert "api-design" in result.output
