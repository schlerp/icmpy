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


def _mark_ran(stage_dir: Path) -> None:
    output = stage_dir / "output"
    output.mkdir(exist_ok=True)
    (output / "_ran.txt").write_text("ran")


def test_reset_workspace_clears_all_run_flags(tmp_path: Path) -> None:
    _make_workspace(tmp_path)
    _mark_ran(tmp_path / "stages" / "01_research")
    _mark_ran(tmp_path / "stages" / "02_script")

    result = runner.invoke(app, ["reset", "--workspace", str(tmp_path)])
    assert result.exit_code == 0
    assert "Cleared run flag" in result.output
    assert "Reset 2 stage(s)" in result.output
    assert "_ran.txt" not in result.output

    assert not (tmp_path / "stages" / "01_research" / "output" / "_ran.txt").exists()
    assert not (tmp_path / "stages" / "02_script" / "output" / "_ran.txt").exists()


def test_reset_workspace_preserves_output_files(tmp_path: Path) -> None:
    _make_workspace(tmp_path)
    research_output = tmp_path / "stages" / "01_research" / "output"
    research_output.mkdir()
    (research_output / "_ran.txt").write_text("ran")
    (research_output / "summary.md").write_text("summary contents")

    result = runner.invoke(app, ["reset", "--workspace", str(tmp_path)])
    assert result.exit_code == 0

    assert (research_output / "summary.md").is_file()
    assert not (research_output / "_ran.txt").exists()


def test_reset_stage_by_number(tmp_path: Path) -> None:
    _make_workspace(tmp_path)
    _mark_ran(tmp_path / "stages" / "01_research")
    _mark_ran(tmp_path / "stages" / "02_script")

    result = runner.invoke(app, ["reset", "01", "--workspace", str(tmp_path)])
    assert result.exit_code == 0
    assert "01 Research" in result.output
    assert "02 Script" not in result.output

    assert not (tmp_path / "stages" / "01_research" / "output" / "_ran.txt").exists()
    assert (tmp_path / "stages" / "02_script" / "output" / "_ran.txt").is_file()


def test_reset_remove_outputs_deletes_output_directory(tmp_path: Path) -> None:
    _make_workspace(tmp_path)
    research_output = tmp_path / "stages" / "01_research" / "output"
    research_output.mkdir()
    (research_output / "_ran.txt").write_text("ran")
    (research_output / "summary.md").write_text("summary contents")

    result = runner.invoke(app, ["reset", "01", "--workspace", str(tmp_path), "--remove-outputs"])
    assert result.exit_code == 0
    assert "Removed outputs" in result.output
    assert not research_output.exists()


def test_reset_dry_run_does_not_delete(tmp_path: Path) -> None:
    _make_workspace(tmp_path)
    _mark_ran(tmp_path / "stages" / "01_research")

    result = runner.invoke(app, ["--dry-run", "reset", "--workspace", str(tmp_path)])
    assert result.exit_code == 0
    assert "dry-run:" in result.output
    assert (tmp_path / "stages" / "01_research" / "output" / "_ran.txt").is_file()


def test_reset_unknown_stage(tmp_path: Path) -> None:
    _make_workspace(tmp_path)
    result = runner.invoke(app, ["reset", "99", "--workspace", str(tmp_path)])
    assert result.exit_code == 1
    assert "Stage not found" in result.output


def test_reset_invalid_workspace(tmp_path: Path) -> None:
    result = runner.invoke(app, ["reset", "--workspace", str(tmp_path / "nowhere")])
    assert result.exit_code == 1
    assert "Invalid workspace" in result.output
