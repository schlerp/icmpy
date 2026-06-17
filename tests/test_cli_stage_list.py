from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from icmpy.cli import app
from icmpy.scaffold import create_workspace


runner = CliRunner()


def _write_valid_workspace(path: Path) -> None:
    create_workspace(path)
    research = path / "stages" / "01_research"
    script = path / "stages" / "02_script"
    research.mkdir()
    script.mkdir()
    (research / "CONTEXT.md").write_text(
        "# Research\n\n## Inputs\n\n- source material\n\n## Process\n\nAnalyze.\n\n## Outputs\n\n- summary.md\n"
    )
    (script / "CONTEXT.md").write_text(
        "# Script\n\n## Inputs\n\n- summary.md\n\n## Process\n\nWrite.\n\n## Outputs\n\n- script.md\n"
    )


def test_stage_list_shows_stages(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    _write_valid_workspace(workspace)
    result = runner.invoke(app, ["stage", "list", "--workspace", str(workspace)])
    assert result.exit_code == 0
    assert "Research" in result.output
    assert "Script" in result.output


def test_stage_list_invalid_workspace(tmp_path: Path) -> None:
    result = runner.invoke(app, ["stage", "list", "--workspace", str(tmp_path / "nowhere")])
    assert result.exit_code == 1
    assert "Invalid workspace" in result.output


def test_stage_list_verbose(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    _write_valid_workspace(workspace)
    result = runner.invoke(app, ["-V", "stage", "list", "--workspace", str(workspace)])
    assert result.exit_code == 0
    # With verbose mode, inputs and outputs columns should appear
    assert "source material" in result.output
    assert "summary.md" in result.output
    assert "script.md" in result.output
