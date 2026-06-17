from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from icmpy.cli import app

runner = CliRunner()


def test_build_list_shows_templates() -> None:
    result = runner.invoke(app, ["build", "list"])
    assert result.exit_code == 0
    assert "Available built-in templates" in result.output
    assert "empty" in result.output
    assert "script-to-animation" in result.output


def test_build_create_requires_template(tmp_path: Path) -> None:
    result = runner.invoke(app, ["build", "create", "--target", str(tmp_path)])
    assert result.exit_code == 1
    assert "No template selected" in result.output


def test_build_create_with_answers_file(tmp_path: Path) -> None:
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
            "create",
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


def test_build_create_with_missing_answers_file(tmp_path: Path) -> None:
    target = tmp_path / "built"
    result = runner.invoke(
        app,
        [
            "build",
            "create",
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
