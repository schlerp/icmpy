from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from icmpy.cli import app
from icmpy.scaffold import CLAUDE_MD_TEMPLATE, CONTEXT_MD_TEMPLATE, create_workspace


runner = CliRunner()


def test_create_workspace_scaffolds_files(tmp_path: Path) -> None:
    target = tmp_path / "my_workspace"
    target.mkdir(parents=True)
    create_workspace(target)

    assert target.is_dir()
    assert (target / "CLAUDE.md").is_file()
    assert (target / "CONTEXT.md").is_file()
    assert (target / "_config" / "voice.md").is_file()
    assert (target / "stages").is_dir()


def test_create_workspace_fails_if_not_empty(tmp_path: Path) -> None:
    target = tmp_path / "existing"
    target.mkdir()
    (target / "file.txt").write_text("hello")
    with pytest.raises(FileExistsError):
        create_workspace(target)


def test_claude_template_includes_workspace_name() -> None:
    rendered = CLAUDE_MD_TEMPLATE.format(name="demo")
    assert "# demo — ICM Workspace" in rendered


def test_context_template_includes_workspace_name() -> None:
    rendered = CONTEXT_MD_TEMPLATE.format(name="demo")
    assert "# demo — Workspace Routing" in rendered


def test_cli_init_creates_workspace(tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", "new_ws", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "new_ws" / "CLAUDE.md").is_file()
    assert (tmp_path / "new_ws" / "CONTEXT.md").is_file()


def test_cli_init_dry_run_does_not_create(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--dry-run", "init", "new_ws", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert not (tmp_path / "new_ws").exists()
    assert "Would create ICM workspace" in result.output


def test_cli_init_verbose_shows_layers(tmp_path: Path) -> None:
    result = runner.invoke(app, ["-VV", "init", "new_ws", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert "Layer 0" in result.output
    assert "Layer 1" in result.output
    assert "Layer 3" in result.output
