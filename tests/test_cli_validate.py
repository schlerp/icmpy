from __future__ import annotations

import os
from pathlib import Path

from typer.testing import CliRunner

from icmpy.cli import app
from icmpy.scaffold import create_workspace


runner = CliRunner()


def _write_valid_workspace(path: Path) -> None:
    create_workspace(path)
    stages = path / "stages"
    research = stages / "01_research"
    research.mkdir()
    (research / "CONTEXT.md").write_text(
        "# Research\n\n## Inputs\n\n- Source material\n\n## Process\n\nAnalyze.\n\n## Outputs\n\n- summary.md\n"
    )


def test_validate_command_passes_valid_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "valid_ws"
    workspace.mkdir(parents=True)
    _write_valid_workspace(workspace)
    result = runner.invoke(app, ["validate", "--workspace", str(workspace)])
    assert result.exit_code == 0
    assert "valid ICM structure" in result.output


def test_validate_command_fails_invalid_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "invalid_ws"
    workspace.mkdir(parents=True)
    create_workspace(workspace)  # only scaffold, no stage folders
    result = runner.invoke(app, ["validate", "--workspace", str(workspace)])
    assert result.exit_code == 1
    assert "validation failed" in result.output


def test_validate_command_default_cwd(tmp_path: Path) -> None:
    # Typer/CliRunner resolves Path.cwd() at import time? Use monkeypatch via tmp cwd.
    # Actually CLI code default runs at invocation. The issue is that changing os.getcwd()
    # after import may not affect Path.cwd() because it caches? Let's use a subprocess
    # or set cwd on the runner. CliRunner doesn't support cwd, so we use an absolute
    # path default and invoke with no args after chdir.
    workspace = tmp_path / "cwd_ws"
    workspace.mkdir(parents=True)
    _write_valid_workspace(workspace)
    original_cwd = os.getcwd()
    try:
        os.chdir(workspace)
        result = runner.invoke(app, ["validate"])
        assert result.exit_code == 0, result.output
        assert "valid ICM structure" in result.output
    finally:
        os.chdir(original_cwd)
