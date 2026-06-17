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
    try:
        with questionnaire_path.open(encoding="utf-8") as f:
            items = json.load(f)
    except json.JSONDecodeError as exc:
        raise TemplateError(f"Invalid questionnaire JSON: {exc}") from exc
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


def _is_stage_folder(name: str) -> bool:
    """True if *name* looks like a numbered stage directory."""
    import re

    return bool(re.match(r"^\d{2,}_[^_].*$", name))


def _stage_title(stage_dir: Path) -> str:
    """Return the title line from a stage CONTEXT.md, or the directory name."""
    contract = stage_dir / "CONTEXT.md"
    if contract.is_file():
        first = contract.read_text(encoding="utf-8").splitlines()[0].strip()
        if first.startswith("# "):
            return first.lstrip("# ").strip()
    return stage_dir.name


def validate_template(template_name: str, answers: dict[str, Any] | None = None) -> list[str]:
    """Return a list of validation errors for *template_name*.

    An empty list means the template is renderable and well-formed.
    """
    errors: list[str] = []
    try:
        manifest = load_template_manifest_entry(template_name)
    except TemplateError as exc:
        return [str(exc)]

    template_dir = _templates_root() / manifest["path"]
    if not template_dir.is_dir():
        return [f"Template directory not found: {template_dir}"]

    try:
        load_questionnaire(template_dir)
    except TemplateError as exc:
        return [str(exc)]

    # Render every template file with dummy answers to surface Jinja2 errors.
    last_rel = "<unknown>"
    try:
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        for source in sorted(template_dir.rglob("*")):
            if not source.is_file() or source.name == "questionnaire.json":
                continue
            rel = source.relative_to(template_dir).as_posix()
            last_rel = rel
            template = env.get_template(rel)
            template.render(**(answers or {}))
    except Exception as exc:  # pragma: no cover - generic template errors
        return [f"Template render error in '{last_rel}': {exc}"]

    # Check that every top-level stage directory has a CONTEXT.md contract.
    stages_dir = template_dir / "stages"
    if stages_dir.is_dir():
        for stage_dir in sorted(stages_dir.iterdir()):
            if not stage_dir.is_dir() or not _is_stage_folder(stage_dir.name):
                continue
            contract = stage_dir / "CONTEXT.md"
            if not contract.is_file():
                errors.append(f"Stage {stage_dir.name} is missing CONTEXT.md")

    return errors


def template_info(template_name: str) -> dict[str, Any]:
    """Return structural information about a template for display."""
    manifest = load_template_manifest_entry(template_name)
    template_dir = _templates_root() / manifest["path"]
    questionnaire = load_questionnaire(template_dir)

    stages_dir = template_dir / "stages"
    stages: list[dict[str, str]] = []
    if stages_dir.is_dir():
        for stage_dir in sorted(stages_dir.iterdir()):
            if stage_dir.is_dir() and _is_stage_folder(stage_dir.name):
                stages.append({"directory": stage_dir.name, "name": _stage_title(stage_dir)})

    return {
        "name": template_name,
        "description": manifest["description"],
        "questions": [
            {
                "key": item.get("key", "unknown"),
                "type": item.get("type", "text"),
                "default": item.get("default", ""),
            }
            for item in questionnaire
        ],
        "stages": stages,
    }
