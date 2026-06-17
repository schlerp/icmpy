from __future__ import annotations

from pathlib import Path

from icmpy.scaffold import create_workspace
from icmpy.stages import next_pending_stage


def test_next_pending_stage_returns_first_empty_stage(tmp_path: Path) -> None:
    create_workspace(tmp_path)
    stages = tmp_path / "stages"
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

- summary.md

## Process

Write.

## Outputs

- script.md
"""
    )
    # Mark stage 01 completed by populating its output
    (stages / "01_research" / "output").mkdir()
    (stages / "01_research" / "output" / "summary.md").write_text("summary")

    pending = next_pending_stage(tmp_path)
    assert pending is not None
    assert pending.directory == "02_script"
