from __future__ import annotations

from pathlib import Path

from icmpy.scaffold import create_workspace
from icmpy.stages import RUN_FLAG, clear_stage, discover_stages


def _workspace_with_two_stages(path: Path) -> None:
    create_workspace(path)
    research = path / "stages" / "01_research"
    script = path / "stages" / "02_script"
    research.mkdir()
    script.mkdir()
    (research / "CONTEXT.md").write_text(
        """# Research

## Inputs

- source material

## Process

Analyze.

## Outputs

- summary.md
"""
    )
    (script / "CONTEXT.md").write_text(
        """# Script

## Inputs

- summary.md

## Process

Write.

## Outputs

- script.md
"""
    )


def test_clear_stage_removes_run_flag_and_empty_output_dir(tmp_path: Path) -> None:
    _workspace_with_two_stages(tmp_path)
    research = tmp_path / "stages" / "01_research"
    output_dir = research / "output"
    output_dir.mkdir()
    run_flag = output_dir / RUN_FLAG
    run_flag.write_text("ran")
    output_file = output_dir / "summary.md"
    output_file.write_text("summary contents")

    stages = discover_stages(tmp_path)
    assert stages[0].status == "completed"
    assert stages[1].status == "pending"

    removed = clear_stage(stages[0])

    assert run_flag in removed
    assert output_file not in removed
    assert output_file.exists()
    assert output_dir.exists()
    assert not run_flag.exists()
    stages = discover_stages(tmp_path)
    assert stages[0].status == "pending"


def test_clear_stage_remove_outputs_deletes_output_directory(tmp_path: Path) -> None:
    _workspace_with_two_stages(tmp_path)
    research = tmp_path / "stages" / "01_research"
    output_dir = research / "output"
    output_dir.mkdir()
    (output_dir / RUN_FLAG).write_text("ran")
    (output_dir / "summary.md").write_text("summary contents")
    (output_dir / "extra" / "nested.txt").parent.mkdir(parents=True)
    (output_dir / "extra" / "nested.txt").write_text("nested")

    stages = discover_stages(tmp_path)
    removed = clear_stage(stages[0], remove_outputs=True)

    assert output_dir in removed
    assert not output_dir.exists()


def test_clear_stage_no_action_when_not_run(tmp_path: Path) -> None:
    _workspace_with_two_stages(tmp_path)
    stages = discover_stages(tmp_path)
    removed = clear_stage(stages[0])
    assert removed == []


def test_clear_stage_dry_run_does_not_change_files(tmp_path: Path) -> None:
    _workspace_with_two_stages(tmp_path)
    research = tmp_path / "stages" / "01_research"
    output_dir = research / "output"
    output_dir.mkdir()
    (output_dir / RUN_FLAG).write_text("ran")
    (output_dir / "summary.md").write_text("summary contents")

    stages = discover_stages(tmp_path)
    removed = clear_stage(stages[0], remove_outputs=True, dry_run=True)

    assert removed
    assert (output_dir / RUN_FLAG).is_file()
    assert (output_dir / "summary.md").is_file()
