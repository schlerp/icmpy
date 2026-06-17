from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from icmpy.cli import app

runner = CliRunner()


def test_build_with_answers_file(tmp_path: Path) -> None:
    answers = tmp_path / "answers.json"
    answers.write_text(
        '{"workspace_name": "auto-lp", "product_name": "AutoTool", '
        '"value_prop": "Do it automatically", "audience": "engineers", "cta": "Try it"}'
    )
    target = tmp_path / "built"
    result = runner.invoke(
        app,
        [
            "build",
            "--template",
            "landing-page",
            "--target",
            str(target),
            "--answers-file",
            str(answers),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Built workspace" in result.output
    assert (target / "auto-lp" / "CLAUDE.md").is_file()


def test_build_with_missing_answers_file(tmp_path: Path) -> None:
    target = tmp_path / "built"
    result = runner.invoke(
        app,
        [
            "build",
            "--template",
            "landing-page",
            "--target",
            str(target),
            "--answers-file",
            str(tmp_path / "missing.json"),
        ],
    )
    assert result.exit_code == 1
    assert "Answers file not found" in result.output
