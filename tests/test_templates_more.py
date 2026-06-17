from __future__ import annotations

from pathlib import Path

from icmpy.builder import build_workspace


def test_literature_review_builds(tmp_path: Path) -> None:
    workspace = build_workspace(
        "literature-review",
        tmp_path,
        answers={
            "workspace_name": "my-review",
            "topic": "LLM context compression",
            "field": "NLP",
            "time_range": "2022-2025",
            "min_sources": "15",
        },
        validate=True,
    )
    assert (workspace / "stages" / "01_search" / "CONTEXT.md").is_file()
    draft = (workspace / "stages" / "05_draft" / "CONTEXT.md").read_text()
    assert "LLM context compression" in draft
    voice = (workspace / "_config" / "voice.md").read_text()
    assert "15" in voice


def test_competitive_analysis_builds(tmp_path: Path) -> None:
    workspace = build_workspace(
        "competitive-analysis",
        tmp_path,
        answers={
            "workspace_name": "my-analysis",
            "product_area": "AI note-taking",
            "market": "SME",
            "competitors": "Notion, Obsidian",
        },
        validate=True,
    )
    strategy = (workspace / "stages" / "04_strategy_brief" / "CONTEXT.md").read_text()
    assert "AI note-taking" in strategy
    assert "SME" in strategy


def test_landing_page_builds(tmp_path: Path) -> None:
    workspace = build_workspace(
        "landing-page",
        tmp_path,
        answers={
            "workspace_name": "my-lp",
            "product_name": "SnapDocs",
            "value_prop": "Build docs in minutes",
            "audience": "startup founders",
            "cta": "Start free trial",
        },
        validate=True,
    )
    copy_stage = (workspace / "stages" / "03_copy" / "CONTEXT.md").read_text()
    assert "SnapDocs" in copy_stage
    assert "Start free trial" in (workspace / "_config" / "voice.md").read_text()


def test_campaign_brief_builds(tmp_path: Path) -> None:
    workspace = build_workspace(
        "campaign-brief",
        tmp_path,
        answers={
            "workspace_name": "my-campaign",
            "campaign_name": "Summer Launch",
            "objective": "Increase demos",
            "audience": "engineering managers",
            "budget": "50k",
        },
        validate=True,
    )
    plan = (workspace / "stages" / "04_channel_plan" / "CONTEXT.md").read_text()
    assert "Summer Launch" in plan
    assert "engineering managers" in plan


def test_client_onboarding_builds(tmp_path: Path) -> None:
    workspace = build_workspace(
        "client-onboarding",
        tmp_path,
        answers={
            "workspace_name": "my-onboarding",
            "client_name": "Acme Corp",
            "service": "AI workflow setup",
            "stakeholder": "Jane Doe",
            "kickoff_date": "2025-07-01",
        },
        validate=True,
    )
    launch = (workspace / "stages" / "04_launch_checklist" / "CONTEXT.md").read_text()
    assert "Acme Corp" in launch
    assert "2025-07-01" in launch
