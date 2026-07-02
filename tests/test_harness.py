from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from icmpy.cli import app
from icmpy.harness import HarnessError, list_harnesses, run_harness
from icmpy.scaffold import create_workspace

runner = CliRunner()


def _write_workspace(path: Path) -> None:
    create_workspace(path)
    research = path / "stages" / "01_research"
    research.mkdir()
    (research / "CONTEXT.md").write_text(
        """# Research

## Inputs

- None

## Process

Research the topic.

## Outputs

- summary.md
"""
    )


def test_list_harnesses() -> None:
    assert set(list_harnesses()) == {"claude", "codex", "opencode", "pi"}


def test_run_harness_unknown() -> None:
    with pytest.raises(HarnessError, match="Unknown harness 'unknown'"):
        run_harness(
            "unknown",
            "bundle",
            workspace_path=Path.cwd(),
            stage_dir=Path.cwd(),
        )


def _make_subprocess_result(stdout: str = "fake harness response", returncode: int = 0) -> object:
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = ""
    return result


def test_run_harness_claude_stdin(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    stage_dir = workspace / "stages" / "01_research"
    stage_dir.mkdir(parents=True)

    with (
        patch("icmpy.harness.shutil.which", return_value="/usr/bin/claude"),
        patch("icmpy.harness.subprocess.run") as mock_run,
    ):
        mock_run.return_value = _make_subprocess_result("claude output")
        stdout, command = run_harness(
            "claude",
            "bundle text",
            workspace_path=workspace,
            stage_dir=stage_dir,
        )

    assert stdout == "claude output"
    assert command[0] == "claude"
    assert command[1] == "-p"
    assert command[-2] == "--max-turns"
    assert command[-1] == "10"
    assert mock_run.call_args.kwargs["input"] == "bundle text"
    assert mock_run.call_args.kwargs["cwd"] == workspace


def test_run_harness_opencode_uses_file_arg(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    stage_dir = workspace / "stages" / "01_research"
    stage_dir.mkdir(parents=True)

    with (
        patch("icmpy.harness.shutil.which", return_value="/usr/bin/opencode"),
        patch("icmpy.harness.subprocess.run") as mock_run,
    ):
        mock_run.return_value = _make_subprocess_result("opencode output")
        stdout, command = run_harness(
            "opencode",
            "bundle text",
            workspace_path=workspace,
            stage_dir=stage_dir,
        )

    assert stdout == "opencode output"
    assert command[0] == "opencode"
    assert command[1] == "run"
    assert "-f" in command
    bundle_file = command[command.index("-f") + 1]
    assert Path(bundle_file).exists()
    assert Path(bundle_file).read_text(encoding="utf-8") == "bundle text"


def test_run_harness_codex_references_file_in_prompt(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    stage_dir = workspace / "stages" / "01_research"
    stage_dir.mkdir(parents=True)

    with (
        patch("icmpy.harness.shutil.which", return_value="/usr/bin/codex"),
        patch("icmpy.harness.subprocess.run") as mock_run,
    ):
        mock_run.return_value = _make_subprocess_result("codex output")
        stdout, command = run_harness(
            "codex",
            "bundle text",
            workspace_path=workspace,
            stage_dir=stage_dir,
        )

    assert stdout == "codex output"
    assert command[0] == "codex"
    assert command[1] == "exec"
    assert any("bundle" in part for part in command)
    # The bundle file should exist even though codex receives it by reference.
    assert list(stage_dir.glob("harness_bundle_*.md"))


def test_run_harness_missing_command(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    stage_dir = workspace / "stages" / "01_research"
    stage_dir.mkdir(parents=True)

    with patch("icmpy.harness.shutil.which", return_value=None):
        with pytest.raises(HarnessError, match="Harness command 'claude' not found"):
            run_harness("claude", "bundle", workspace_path=workspace, stage_dir=stage_dir)


def test_run_harness_nonzero_exit(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    stage_dir = workspace / "stages" / "01_research"
    stage_dir.mkdir(parents=True)

    with (
        patch("icmpy.harness.shutil.which", return_value="/usr/bin/claude"),
        patch("icmpy.harness.subprocess.run") as mock_run,
    ):
        mock_run.return_value = _make_subprocess_result(stdout="", returncode=1)
        with pytest.raises(HarnessError, match="Harness 'claude' exited with code 1"):
            run_harness("claude", "bundle", workspace_path=workspace, stage_dir=stage_dir)


def test_run_harness_pi_uses_at_file(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    stage_dir = workspace / "stages" / "01_research"
    stage_dir.mkdir(parents=True)

    with (
        patch("icmpy.harness.shutil.which", return_value="/usr/bin/pi"),
        patch("icmpy.harness.subprocess.run") as mock_run,
    ):
        mock_run.return_value = _make_subprocess_result("pi output")
        stdout, command = run_harness(
            "pi",
            "bundle text",
            workspace_path=workspace,
            stage_dir=stage_dir,
        )

    assert stdout == "pi output"
    assert command[0] == "pi"
    assert command[1] == "-p"
    at_arg = command[-1]
    assert at_arg.startswith("@")
    bundle_file = Path(at_arg[1:])
    assert bundle_file.exists()
    assert bundle_file.read_text(encoding="utf-8") == "bundle text"


def test_cli_stage_run_with_harness(tmp_path: Path) -> None:
    _write_workspace(tmp_path)

    with patch("icmpy.cli.run_harness") as mock_run:
        mock_run.return_value = ("harness response", ["claude", "-p", "..."])
        result = runner.invoke(
            app,
            [
                "stage",
                "run",
                "01",
                "--workspace",
                str(tmp_path),
                "--harness",
                "claude",
            ],
        )

    assert result.exit_code == 0
    assert "Dispatched to harness" in result.output
    assert "harness response" not in result.output
    response_file = tmp_path / "stages" / "01_research" / "output" / "claude.md"
    assert response_file.read_text(encoding="utf-8") == "harness response"
    assert (tmp_path / "stages" / "01_research" / "output" / "_ran.txt").is_file()


def test_cli_stage_run_with_harness_dry_run(tmp_path: Path) -> None:
    _write_workspace(tmp_path)

    result = runner.invoke(
        app,
        [
            "--dry-run",
            "stage",
            "run",
            "01",
            "--workspace",
            str(tmp_path),
            "--harness",
            "claude",
        ],
    )

    assert result.exit_code == 0
    assert "Would run" in result.output
    assert not (tmp_path / "stages" / "01_research" / "output" / "claude.md").exists()


def test_cli_stage_run_unknown_harness(tmp_path: Path) -> None:
    _write_workspace(tmp_path)

    result = runner.invoke(
        app,
        [
            "stage",
            "run",
            "01",
            "--workspace",
            str(tmp_path),
            "--harness",
            "not-real",
        ],
    )

    assert result.exit_code == 1
    assert "Harness error" in result.output


def test_cli_harness_list() -> None:
    result = runner.invoke(app, ["harness", "list"])
    assert result.exit_code == 0
    assert "claude" in result.output
    assert "codex" in result.output
    assert "opencode" in result.output
    assert "pi" in result.output
