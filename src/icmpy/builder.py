from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jinja2 import BaseLoader, Environment, FileSystemLoader

from icmpy.scaffold import CLAUDE_MD_TEMPLATE, CONTEXT_MD_TEMPLATE, VOICE_MD_TEMPLATE
from icmpy.validator import validate_workspace


class TemplateError(Exception):
    """Raised when a workspace template cannot be loaded or rendered."""


def templates_root() -> Path:
    """Return the filesystem root of the built-in templates package."""
    import icmpy

    return Path(icmpy.__file__).parent / "templates"


def _templates_root() -> Path:
    """Backwards-compatible alias for templates_root."""
    return templates_root()


def list_templates() -> list[dict[str, Any]]:
    """Return the list of built-in templates from the manifest."""
    manifest_path = _templates_root() / "builtins_manifest.json"
    with manifest_path.open(encoding="utf-8") as f:
        data = json.load(f)
    return list(data.get("templates", []))


def load_template_manifest_entry(name: str) -> dict[str, Any]:
    """Return a single manifest entry by template name, or raise TemplateError."""
    for template in list_templates():
        if template["name"] == name:
            return template
    available = ", ".join(t["name"] for t in list_templates())
    raise TemplateError(f"Unknown template '{name}'. Available: {available}")


def load_questionnaire(template_dir: Path) -> list[dict[str, Any]]:
    """Load and validate the questionnaire for a template."""
    questionnaire_path = template_dir / "questionnaire.json"
    if not questionnaire_path.is_file():
        return []
    with questionnaire_path.open(encoding="utf-8") as f:
        items = json.load(f)
    if not isinstance(items, list):
        raise TemplateError("questionnaire.json must contain a JSON array")
    return items


def _render_text(text: str, answers: dict[str, Any]) -> str:
    """Render a Jinja2 template string with *answers*."""
    env = Environment(loader=BaseLoader())
    template = env.from_string(text)
    return template.render(**answers)


def build_workspace(
    template_name: str,
    target_dir: Path,
    answers: dict[str, Any] | None = None,
    *,
    validate: bool = True,
) -> Path:
    """Build a new ICM workspace from a built-in template.

    Args:
        template_name: Name of the built-in template (from the manifest).
        target_dir: Directory in which to create the workspace. The final
            workspace folder name is taken from `answers.get("workspace_name")`
            or defaults to the template name.
        answers: Questionnaire answers used to render template files.
        validate: Whether to run validate_workspace on the created workspace.
            Templates intentionally missing stages should pass False.

    Returns:
        The path to the created workspace directory.
    """
    answers = dict(answers or {})
    manifest = load_template_manifest_entry(template_name)
    template_dir = _templates_root() / manifest["path"]

    if not template_dir.is_dir():
        raise TemplateError(f"Template directory not found: {template_dir}")

    workspace_name = answers.get("workspace_name") or template_name
    workspace_path = target_dir / workspace_name

    if workspace_path.exists() and any(workspace_path.iterdir()):
        raise FileExistsError(f"Workspace already exists and is not empty: {workspace_path}")

    # Base scaffold
    workspace_path.mkdir(parents=True, exist_ok=True)
    (workspace_path / "_config").mkdir(exist_ok=True)
    (workspace_path / "stages").mkdir(exist_ok=True)

    (workspace_path / "CLAUDE.md").write_text(
        _render_text(CLAUDE_MD_TEMPLATE, {"name": workspace_name}),
        encoding="utf-8",
    )
    (workspace_path / "CONTEXT.md").write_text(
        _render_text(CONTEXT_MD_TEMPLATE, {"name": workspace_name}),
        encoding="utf-8",
    )
    (workspace_path / "_config" / "voice.md").write_text(
        _render_text(VOICE_MD_TEMPLATE, answers),
        encoding="utf-8",
    )

    # Render template files into the workspace
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    for source in sorted(template_dir.rglob("*")):
        if not source.is_file():
            continue
        rel_path = source.relative_to(template_dir)
        if rel_path.name == "questionnaire.json":
            continue

        destination = workspace_path / rel_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        template = env.get_template(str(rel_path.as_posix()))
        rendered = template.render(**answers)
        destination.write_text(rendered, encoding="utf-8")

    if validate:
        result = validate_workspace(workspace_path)
        if not result.ok:
            errors = "\n".join(f"  • {e}" for e in result.errors)
            raise TemplateError(f"Built workspace failed validation:\n{errors}")

    return workspace_path
