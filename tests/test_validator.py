from __future__ import annotations

import shutil
from pathlib import Path

from icmpy.validator import validate_workspace


def _write_valid_workspace(path: Path) -> None:
    (path / "CLAUDE.md").write_text("# Workspace\n\nIdentity.\n")
    (path / "CONTEXT.md").write_text("# Context\n\nRouting.\n")
    stages = path / "stages"
    stages.mkdir()
    research = stages / "01_research"
    research.mkdir()
    (research / "CONTEXT.md").write_text(
        """# Research

## Inputs

- Source material

## Process

Analyze.

## Outputs

- summary.md
"""
    )


def test_valid_workspace(tmp_workspace: Path) -> None:
    _write_valid_workspace(tmp_workspace)
    result = validate_workspace(tmp_workspace)
    assert result.ok is True
    assert result.errors == []


def test_workspace_path_does_not_exist(tmp_workspace: Path) -> None:
    missing = tmp_workspace / "nowhere"
    result = validate_workspace(missing)
    assert result.ok is False
    assert "does not exist" in result.errors[0]


def test_missing_claude_md(tmp_workspace: Path) -> None:
    _write_valid_workspace(tmp_workspace)
    (tmp_workspace / "CLAUDE.md").unlink()
    result = validate_workspace(tmp_workspace)
    assert result.ok is False
    assert any("CLAUDE.md" in err for err in result.errors)


def test_missing_context_md(tmp_workspace: Path) -> None:
    _write_valid_workspace(tmp_workspace)
    (tmp_workspace / "CONTEXT.md").unlink()
    result = validate_workspace(tmp_workspace)
    assert result.ok is False
    assert any("CONTEXT.md" in err for err in result.errors)


def test_missing_stages_directory(tmp_workspace: Path) -> None:
    _write_valid_workspace(tmp_workspace)
    shutil.rmtree(tmp_workspace / "stages")
    result = validate_workspace(tmp_workspace)
    assert result.ok is False
    assert any("stages/" in err for err in result.errors)


def test_no_stage_folders(tmp_workspace: Path) -> None:
    _write_valid_workspace(tmp_workspace)
    for subdir in (tmp_workspace / "stages").iterdir():
        if subdir.is_dir():
            shutil.rmtree(subdir)
    result = validate_workspace(tmp_workspace)
    assert result.ok is False
    assert any("No numbered stage folders" in err for err in result.errors)


def test_missing_stage_context(tmp_workspace: Path) -> None:
    _write_valid_workspace(tmp_workspace)
    (tmp_workspace / "stages" / "01_research" / "CONTEXT.md").unlink()
    result = validate_workspace(tmp_workspace)
    assert result.ok is False
    assert any("Missing stage contract" in err for err in result.errors)


def test_stage_context_missing_section(tmp_workspace: Path) -> None:
    _write_valid_workspace(tmp_workspace)
    (tmp_workspace / "stages" / "01_research" / "CONTEXT.md").write_text(
        "# Research\n\n## Inputs\n\n- Source\n\n## Outputs\n\n- summary.md\n"
    )
    result = validate_workspace(tmp_workspace)
    assert result.ok is False
    assert any("missing '## Process'" in err for err in result.errors)


def test_non_sequential_stage_numbering(tmp_workspace: Path) -> None:
    _write_valid_workspace(tmp_workspace)
    (tmp_workspace / "stages" / "01_research").rename(tmp_workspace / "stages" / "03_research")
    result = validate_workspace(tmp_workspace)
    assert result.ok is False
    assert any("Non-sequential" in err for err in result.errors)
