from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from icmpy.cli import app

runner = CliRunner()


def test_build_info_shows_stages_and_questions() -> None:
    result = runner.invoke(app, ["build", "info", "script-to-animation"])
    assert result.exit_code == 0, result.output
    assert "Research" in result.output
    assert "Production" in result.output


def test_build_info_unknown_template() -> None:
    result = runner.invoke(app, ["build", "info", "not-a-template"])
    assert result.exit_code == 1
    assert "Unknown template" in result.output


def test_build_create_validates_template_before_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from icmpy import builder

    templates_dir = tmp_path / "templates"
    template_dir = templates_dir / "broken"
    template_dir.mkdir(parents=True)
    (templates_dir / "builtins_manifest.json").write_text(
        '{"templates": [{"name": "broken", "description": "Bad", "path": "broken"}]}'
    )
    (template_dir / "questionnaire.json").write_text("[]")
    (template_dir / "stages" / "01_broken").mkdir(parents=True)

    monkeypatch.setattr(builder, "_templates_root", lambda: templates_dir)

    result = runner.invoke(
        app,
        ["build", "create", "--template", "broken", "--target", str(tmp_path)],
    )
    assert result.exit_code == 1
    assert "failed validation" in result.output
    assert "missing CONTEXT.md" in result.output
