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


def test_stage_run_next_selects_first_pending(tmp_path: Path) -> None:
    _make_workspace(tmp_path)
    result = runner.invoke(app, ["stage", "run", "next", "--workspace", str(tmp_path)])
    assert result.exit_code == 0
    assert "Next pending stage" in result.output
    assert "01 Research" in result.output


def test_stage_run_no_args_selects_next(tmp_path: Path) -> None:
    _make_workspace(tmp_path)
    result = runner.invoke(app, ["stage", "run", "--workspace", str(tmp_path)])
    assert result.exit_code == 0
    assert "Next pending stage" in result.output


def test_stage_run_next_when_all_complete(tmp_path: Path) -> None:
    _make_workspace(tmp_path)
    (tmp_path / "stages" / "01_research" / "output").mkdir()
    (tmp_path / "stages" / "01_research" / "output" / "summary.md").write_text("ok")
    (tmp_path / "stages" / "02_script" / "output").mkdir()
    (tmp_path / "stages" / "02_script" / "output" / "script.md").write_text("ok")
    result = runner.invoke(app, ["stage", "run", "next", "--workspace", str(tmp_path)])
    assert result.exit_code == 0
    assert "All stages are complete" in result.output
