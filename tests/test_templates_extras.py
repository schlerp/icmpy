from __future__ import annotations

from pathlib import Path

import pytest

from icmpy.builder import build_workspace, list_templates


@pytest.mark.parametrize(
    ("name", "expected_stages"),
    [
        ("long-form-essay", ["01_idea", "02_research", "03_outline", "04_draft", "05_edit"]),
        (
            "course-module",
            [
                "01_learning_design",
                "02_outline",
                "03_content_draft",
                "04_slides",
                "05_assessment",
            ],
        ),
        ("weekly-report", ["01_data_gather", "02_highlights", "03_narrative", "04_review"]),
    ],
)
def test_new_templates_build_and_validate(
    name: str, expected_stages: list[str], tmp_path: Path
) -> None:
    templates = {t["name"]: t for t in list_templates()}
    assert name in templates

    workspace = build_workspace(
        name,
        tmp_path,
        answers={
            "workspace_name": f"test-{name}",
            "topic": "Test Topic",
            "audience": "Test Audience",
            "target_word_count": "1200",
            "learning_objective": "Learn testing",
            "module_duration": "30",
            "report_title": "Test Report",
            "reporting_period": "Week 1",
            "data_source": "test dashboard",
        },
        validate=True,
    )

    assert workspace.is_dir()
    for stage_dir in expected_stages:
        stage_context = workspace / "stages" / stage_dir / "CONTEXT.md"
        assert stage_context.is_file(), f"missing {stage_context}"


def test_long_form_essay_substitutions(tmp_path: Path) -> None:
    workspace = build_workspace(
        "long-form-essay",
        tmp_path,
        answers={
            "workspace_name": "my-essay",
            "topic": "AI Safety",
            "audience": "engineers",
            "target_word_count": "1500",
        },
        validate=True,
    )
    draft = workspace / "stages" / "04_draft" / "CONTEXT.md"
    assert "1500" in draft.read_text()
    assert "AI Safety" in (workspace / "stages" / "01_idea" / "CONTEXT.md").read_text()
    assert "engineers" in (workspace / "_config" / "voice.md").read_text()


def test_course_module_substitutions(tmp_path: Path) -> None:
    workspace = build_workspace(
        "course-module",
        tmp_path,
        answers={
            "workspace_name": "my-course",
            "topic": "Testing",
            "audience": "new hires",
            "learning_objective": "write unit tests",
            "module_duration": "45",
        },
        validate=True,
    )
    assert "45" in (workspace / "stages" / "02_outline" / "CONTEXT.md").read_text()
    learning_design = workspace / "stages" / "01_learning_design" / "CONTEXT.md"
    assert "write unit tests" in learning_design.read_text()


def test_weekly_report_substitutions(tmp_path: Path) -> None:
    workspace = build_workspace(
        "weekly-report",
        tmp_path,
        answers={
            "workspace_name": "my-report",
            "report_title": "Sprint Review",
            "reporting_period": "June 9-13",
            "audience": "leadership",
            "data_source": "Jira",
        },
        validate=True,
    )
    assert "Sprint Review" in (workspace / "stages" / "03_narrative" / "CONTEXT.md").read_text()
    assert "Jira" in (workspace / "stages" / "01_data_gather" / "CONTEXT.md").read_text()
