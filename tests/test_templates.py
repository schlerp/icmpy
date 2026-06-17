from __future__ import annotations

from pathlib import Path

from icmpy.builder import build_workspace, list_templates, templates_root


def test_script_to_animation_template_in_manifest() -> None:
    templates = list_templates()
    names = [t["name"] for t in templates]
    assert "script-to-animation" in names


def test_build_script_to_animation_workspace(tmp_path: Path) -> None:
    workspace = build_workspace(
        "script-to-animation",
        tmp_path,
        answers={
            "workspace_name": "ai-safety-video",
            "topic": "AI Safety",
            "target_duration": "90",
        },
        validate=True,
    )

    assert workspace.is_dir()
    assert (workspace / "CLAUDE.md").is_file()
    assert (workspace / "CONTEXT.md").is_file()
    assert (workspace / "_config" / "voice.md").is_file()
    assert (workspace / "_config" / "structure.md").is_file()

    # Stage contracts
    research_context = workspace / "stages" / "01_research" / "CONTEXT.md"
    script_context = workspace / "stages" / "02_script" / "CONTEXT.md"
    production_context = workspace / "stages" / "03_production" / "CONTEXT.md"

    assert research_context.is_file()
    assert script_context.is_file()
    assert production_context.is_file()

    # Answers substituted
    assert "AI Safety" in research_context.read_text()
    assert "90" in script_context.read_text()
    assert "90" in production_context.read_text()

    # Topic brief rendered
    topic_brief = workspace / "stages" / "01_research" / "output" / "topic_brief.md"
    assert topic_brief.is_file()
    assert "AI Safety" in topic_brief.read_text()


def test_script_to_animation_template_files_exist() -> None:
    root = templates_root() / "script_to_animation"
    assert (root / "questionnaire.json").is_file()
    assert (root / "_config" / "voice.md").is_file()
    assert (root / "_config" / "structure.md").is_file()
    assert (root / "stages" / "01_research" / "CONTEXT.md").is_file()
    assert (root / "stages" / "02_script" / "CONTEXT.md").is_file()
    assert (root / "stages" / "03_production" / "CONTEXT.md").is_file()


def test_script_to_animation_validates(tmp_path: Path) -> None:
    workspace = build_workspace(
        "script-to-animation",
        tmp_path,
        answers={
            "workspace_name": "validated-ws",
            "topic": "X",
            "target_duration": "60",
        },
        validate=True,
    )
    from icmpy.validator import validate_workspace

    result = validate_workspace(workspace)
    assert result.ok is True
