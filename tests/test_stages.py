from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from icmpy.scaffold import create_workspace
from icmpy.stages import discover_stages, find_stage


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


def test_discover_stages_finds_ordered_stages(tmp_path: Path) -> None:
    _write_valid_workspace(tmp_path)
    stages = discover_stages(tmp_path)
    assert len(stages) == 2
    assert stages[0].number == 1
    assert stages[1].number == 2
    assert stages[0].name == "Research"
    assert stages[1].name == "Script"


def test_discover_stages_marks_completed_with_output(tmp_path: Path) -> None:
    _write_valid_workspace(tmp_path)
    (tmp_path / "stages" / "01_research" / "output").mkdir()
    (tmp_path / "stages" / "01_research" / "output" / "summary.md").write_text("done")
    stages = discover_stages(tmp_path)
    assert stages[0].status == "completed"
    assert stages[1].status == "pending"


def test_find_stage_by_number(tmp_path: Path) -> None:
    _write_valid_workspace(tmp_path)
    stage = find_stage(tmp_path, "01")
    assert stage is not None
    assert stage.name == "Research"


def test_find_stage_by_name(tmp_path: Path) -> None:
    _write_valid_workspace(tmp_path)
    stage = find_stage(tmp_path, "script")
    assert stage is not None
    assert stage.name == "Script"


def test_find_stage_missing(tmp_path: Path) -> None:
    _write_valid_workspace(tmp_path)
    assert find_stage(tmp_path, "03_production") is None
