from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from icmpy.cli import app
from icmpy.scaffold import create_workspace

runner = CliRunner()


def _make_workspace(path: Path) -> None:
    create_workspace(path)
    stages = path / "stages"
    (stages / "01_research").mkdir()
    (stages / "01_research" / "CONTEXT.md").write_text(
        """# Research

## Inputs

- None

## Process

Research.

## Outputs

- summary.md
"""
    )
    (stages / "02_script").mkdir()
    (stages / "02_script" / "CONTEXT.md").write_text(
        """# Script

## Inputs

- ../01_research/output/summary.md

## Process

Write.

## Outputs

- script.md
"""
    )


def test_status_shows_next_stage(tmp_path: Path) -> None:
    _make_workspace(tmp_path)
    result = runner.invoke(app, ["status", "--workspace", str(tmp_path)])
    assert result.exit_code == 0
    assert "01 Research" in result.output
    assert "Next stage" in result.output


def test_status_all_done(tmp_path: Path) -> None:
    _make_workspace(tmp_path)
    (tmp_path / "stages" / "01_research" / "output").mkdir()
    (tmp_path / "stages" / "01_research" / "output" / "summary.md").write_text("ok")
    (tmp_path / "stages" / "02_script" / "output").mkdir()
    (tmp_path / "stages" / "02_script" / "output" / "script.md").write_text("ok")
    result = runner.invoke(app, ["status", "--workspace", str(tmp_path)])
    assert result.exit_code == 0
    assert "all done" in result.output


def test_status_invalid_workspace(tmp_path: Path) -> None:
    result = runner.invoke(app, ["status", "--workspace", str(tmp_path)])
    assert result.exit_code == 1
    assert "validation failed" in result.output
