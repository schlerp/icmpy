from __future__ import annotations

import json
from pathlib import Path

import pytest

from icmpy.builder import (
    TemplateError,
    build_workspace,
    list_templates,
    load_questionnaire,
    load_template_manifest_entry,
)


def test_list_templates_returns_empty_template() -> None:
    templates = list_templates()
    names = [t["name"] for t in templates]
    assert "empty" in names


def test_load_unknown_template_raises() -> None:
    with pytest.raises(TemplateError):
        load_template_manifest_entry("does-not-exist")


def test_load_questionnaire_parses_items(tmp_path: Path) -> None:
    questionnaire = [
        {"key": "topic", "question": "What is the topic?", "type": "text"},
    ]
    questionnaire_path = tmp_path / "questionnaire.json"
    questionnaire_path.write_text(json.dumps(questionnaire))
    loaded = load_questionnaire(tmp_path)
    assert loaded == questionnaire


def test_build_empty_workspace(tmp_path: Path) -> None:
    # The empty template intentionally has no stages, so we skip validation.
    workspace = build_workspace(
        "empty",
        tmp_path,
        answers={"workspace_name": "my-empty-workspace"},
        validate=False,
    )
    assert workspace.is_dir()
    assert (workspace / "CLAUDE.md").is_file()
    assert (workspace / "CONTEXT.md").is_file()


def test_build_workspace_rejects_existing(tmp_path: Path) -> None:
    existing = tmp_path / "my-empty-workspace"
    existing.mkdir()
    (existing / "file.txt").write_text("occupied")
    with pytest.raises(FileExistsError):
        build_workspace(
            "empty",
            tmp_path,
            answers={"workspace_name": "my-empty-workspace"},
            validate=False,
        )
