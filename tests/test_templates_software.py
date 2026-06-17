from __future__ import annotations

from pathlib import Path

from icmpy.builder import build_workspace, list_templates


def test_feature_spec_template_builds(tmp_path: Path) -> None:
    names = {t["name"] for t in list_templates()}
    assert "feature-spec" in names

    workspace = build_workspace(
        "feature-spec",
        tmp_path,
        answers={
            "workspace_name": "my-feature",
            "feature_name": "Dark Mode",
            "problem": "Users want low-light reading",
            "target_user": "mobile readers",
            "success_metric": "settings toggle usage",
        },
        validate=True,
    )
    assert (workspace / "stages" / "01_problem" / "CONTEXT.md").is_file()
    assert (workspace / "stages" / "05_prd" / "CONTEXT.md").is_file()
    prd = (workspace / "stages" / "05_prd" / "CONTEXT.md").read_text()
    assert "Dark Mode" in prd
    assert "mobile readers" in prd


def test_bug_runbook_template_builds(tmp_path: Path) -> None:
    names = {t["name"] for t in list_templates()}
    assert "bug-runbook" in names

    workspace = build_workspace(
        "bug-runbook",
        tmp_path,
        answers={
            "workspace_name": "my-bug",
            "issue_summary": "500 on login",
            "affected_system": "auth service",
            "severity": "critical",
            "reporter": "sre",
        },
        validate=True,
    )
    post = (workspace / "stages" / "05_post_mortem" / "CONTEXT.md").read_text()
    assert "auth service" in post
    assert "critical" in post


def test_api_design_template_builds(tmp_path: Path) -> None:
    names = {t["name"] for t in list_templates()}
    assert "api-design" in names

    workspace = build_workspace(
        "api-design",
        tmp_path,
        answers={
            "workspace_name": "my-api",
            "api_name": "Orders API",
            "consumer": "frontend checkout",
            "base_url": "/api/v2",
            "auth_method": "OAuth2",
        },
        validate=True,
    )
    docs = (workspace / "stages" / "05_documentation" / "CONTEXT.md").read_text()
    assert "/api/v2" in docs
    assert "OAuth2" in (workspace / "_config" / "voice.md").read_text()
