from __future__ import annotations

import json
from pathlib import Path

import pytest

from icmpy import builder
from icmpy.builder import (
    TemplateError,
    load_template_manifest_entry,
    template_info,
    validate_template,
)


def test_validate_template_known_template() -> None:
    assert validate_template("empty") == []


def test_validate_template_unknown_template() -> None:
    errors = validate_template("does-not-exist")
    assert any("Unknown template" in e for e in errors)


def test_validate_template_bad_questionnaire(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    templates_dir = tmp_path / "templates"
    template_dir = templates_dir / "bad_q"
    template_dir.mkdir(parents=True)
    manifest_path = templates_dir / "builtins_manifest.json"
    manifest_path.write_text(
        json.dumps({"templates": [{"name": "bad_q", "description": "Bad", "path": "bad_q"}]})
    )
    (template_dir / "questionnaire.json").write_text("{not valid json")

    monkeypatch.setattr(builder, "_templates_root", lambda: templates_dir)

    errors = validate_template("bad_q")
    assert errors


def test_validate_template_missing_context_md(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    templates_dir = tmp_path / "templates"
    template_dir = templates_dir / "missing_ctx"
    template_dir.mkdir(parents=True)
    manifest_path = templates_dir / "builtins_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "templates": [
                    {
                        "name": "missing_ctx",
                        "description": "Missing CTX",
                        "path": "missing_ctx",
                    }
                ]
            }
        )
    )
    (template_dir / "questionnaire.json").write_text("[]")
    stages = template_dir / "stages"
    (stages / "01_broken").mkdir(parents=True)

    monkeypatch.setattr(builder, "_templates_root", lambda: templates_dir)

    errors = validate_template("missing_ctx")
    assert any("missing CONTEXT.md" in e for e in errors)


def test_template_info_known_template() -> None:
    info = template_info("script-to-animation")
    assert info["name"] == "script-to-animation"
    assert len(info["stages"]) == 3
    assert any(s["directory"].startswith("01_") for s in info["stages"])


def test_template_info_questions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    templates_dir = tmp_path / "templates"
    template_dir = templates_dir / "qa_demo"
    template_dir.mkdir(parents=True)
    (templates_dir / "builtins_manifest.json").write_text(
        json.dumps({"templates": [{"name": "qa_demo", "description": "Demo", "path": "qa_demo"}]})
    )
    (template_dir / "questionnaire.json").write_text(
        json.dumps(
            [
                {"key": "name", "question": "Name?", "type": "text", "default": "X"},
                {"key": "count", "question": "Count?", "type": "integer", "default": "5"},
            ]
        )
    )
    (template_dir / "CLAUDE.md").write_text("# {{ name }}")

    monkeypatch.setattr(builder, "_templates_root", lambda: templates_dir)

    info = template_info("qa_demo")
    assert [q["key"] for q in info["questions"]] == ["name", "count"]


def test_load_manifest_entry_unknown_raises() -> None:
    with pytest.raises(TemplateError):
        load_template_manifest_entry("nope")
