from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from jinja2 import BaseLoader, Environment, FileSystemLoader

from icmpy.scaffold import CLAUDE_MD_TEMPLATE, CONTEXT_MD_TEMPLATE, VOICE_MD_TEMPLATE
from icmpy.template_catalog import (
    AmbiguousTemplateName,
    TemplateCatalog,
    TemplateOrigin,
    get_custom_template_root,
    validate_custom_template,
)
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


def _origin_from_option(origin: TemplateOrigin | str | None) -> TemplateOrigin | None:
    """Normalize a CLI origin option to a TemplateOrigin enum value."""
    if origin is None:
        return None
    if isinstance(origin, TemplateOrigin):
        return origin
    value = str(origin).lower().replace("_", "-")
    for member in TemplateOrigin:
        if value == member.value.lower():
            return member
    raise ValueError(f"Invalid origin: {origin}")


def discover_templates(custom_root: Path | None = None) -> list[dict[str, Any]]:
    """Return all built-in and custom templates as a unified catalog."""
    return TemplateCatalog(custom_root=custom_root, builtin_root=_templates_root()).list_templates()


def list_templates() -> list[dict[str, Any]]:
    """Return the list of built-in templates from the manifest.

    For the unified catalog (built-ins + custom), use ``discover_templates``.
    """
    manifest_path = _templates_root() / "builtins_manifest.json"
    with manifest_path.open(encoding="utf-8") as f:
        data = json.load(f)
    return list(data.get("templates", []))


def load_template_manifest_entry(name: str) -> dict[str, Any]:
    """Return a single built-in manifest entry by template name.

    Raises TemplateError if the template is not a built-in.
    """
    for template in list_templates():
        if template["name"] == name:
            return template
    available = ", ".join(t["name"] for t in list_templates())
    raise TemplateError(f"Unknown built-in template '{name}'. Available: {available}")


def resolve_template(
    name: str,
    origin: TemplateOrigin | str | None = None,
    custom_root: Path | None = None,
) -> dict[str, Any]:
    """Resolve a template name to its path and metadata.

    Returns a dict with ``name``, ``description``, ``origin`` and ``path``.
    Raises TemplateError on ambiguity or if the template is not found.
    """
    catalog = TemplateCatalog(custom_root=custom_root, builtin_root=_templates_root())
    try:
        resolved_origin = _origin_from_option(origin)
    except ValueError as exc:
        raise TemplateError(str(exc)) from exc
    try:
        template = catalog.get(name, origin=resolved_origin)
    except AmbiguousTemplateName as exc:
        raise TemplateError(str(exc)) from exc
    except KeyError as exc:
        raise TemplateError(f"Unknown template '{name}'") from exc

    return {
        "name": template.name,
        "description": template.description,
        "origin": template.origin.value,
        "path": template.path,
    }


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
    origin: TemplateOrigin | str | None = None,
    custom_root: Path | None = None,
) -> Path:
    """Build a new ICM workspace from a built-in or custom template.

    Args:
        template_name: Name of the template.
        target_dir: Directory in which to create the workspace. The final
            workspace folder name is taken from ``answers.get("workspace_name")``
            or defaults to the template name.
        answers: Questionnaire answers used to render template files.
        validate: Whether to run validate_workspace on the created workspace.
        origin: Optional origin filter (``built-in`` or ``custom``) to resolve
            ambiguous template names.
        custom_root: Optional override for the custom template directory.

    Returns:
        The path to the created workspace directory.
    """
    answers = dict(answers or {})
    template = resolve_template(template_name, origin=origin, custom_root=custom_root)
    template_dir = template["path"]

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
        if rel_path == Path("CONTEXT.md"):
            # CONTEXT.md at the template root is template metadata, not the
            # workspace routing file, so leave the scaffold version in place.
            continue

        destination = workspace_path / rel_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        jinja_template = env.get_template(str(rel_path.as_posix()))
        rendered = jinja_template.render(**answers)
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


def validate_template(
    template_name: str,
    answers: dict[str, Any] | None = None,
    origin: TemplateOrigin | str | None = None,
    custom_root: Path | None = None,
) -> list[str]:
    """Return a list of validation errors for *template_name*.

    An empty list means the template is renderable and well-formed.
    """
    errors: list[str] = []
    try:
        template = resolve_template(template_name, origin=origin, custom_root=custom_root)
    except TemplateError as exc:
        return [str(exc)]

    template_dir = template["path"]
    if not template_dir.is_dir():
        return [f"Template directory not found: {template_dir}"]

    template_origin = _origin_from_option(template["origin"])
    if template_origin == TemplateOrigin.CUSTOM:
        custom_errors = validate_custom_template(template_dir)
        if custom_errors:
            errors.extend(custom_errors)

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
            rel = source.relative_to(template_dir)
            if rel == Path("CONTEXT.md"):
                # Root CONTEXT.md is template metadata, not a renderable asset.
                continue
            last_rel = rel.as_posix()
            jinja_template = env.get_template(last_rel)
            jinja_template.render(**(answers or {}))
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


def template_info(
    template_name: str,
    origin: TemplateOrigin | str | None = None,
    custom_root: Path | None = None,
) -> dict[str, Any]:
    """Return structural information about a template for display."""
    template = resolve_template(template_name, origin=origin, custom_root=custom_root)
    template_dir = template["path"]
    questionnaire = load_questionnaire(template_dir)

    stages_dir = template_dir / "stages"
    stages: list[dict[str, str]] = []
    if stages_dir.is_dir():
        for stage_dir in sorted(stages_dir.iterdir()):
            if stage_dir.is_dir() and _is_stage_folder(stage_dir.name):
                stages.append({"directory": stage_dir.name, "name": _stage_title(stage_dir)})

    return {
        "name": template["name"],
        "description": template["description"],
        "origin": template["origin"],
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


def copy_builtin_to_custom(
    source_name: str,
    target_name: str | None = None,
    custom_root: Path | None = None,
) -> Path:
    """Copy a built-in template to the custom template directory.

    Args:
        source_name: Name of the built-in template to copy.
        target_name: Optional name for the custom copy. Defaults to *source_name*.
        custom_root: Optional override for the custom template directory.

    Returns:
        Path to the new custom template directory.

    Raises:
        TemplateError: when the source built-in template is unknown.
        FileExistsError: when the destination already exists.
    """
    destination_root = custom_root or get_custom_template_root()
    custom_entry = resolve_template(source_name, origin=TemplateOrigin.BUILTIN)
    source_dir = custom_entry["path"]
    target_name = target_name or source_name
    destination = destination_root / target_name

    if destination.exists():
        raise FileExistsError(f"Custom template already exists: {destination}")

    destination_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, destination)

    context_md = destination / "CONTEXT.md"
    if not context_md.is_file():
        description = custom_entry.get("description", f"Custom {source_name} template")
        context_md.write_text(
            f"---\npurpose: {description}\n---\n\n# {target_name}\n\n"
            f"Custom copy of the {source_name} template.\n",
            encoding="utf-8",
        )

    return destination
