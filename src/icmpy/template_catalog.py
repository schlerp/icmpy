from __future__ import annotations

import os
import platform
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import platformdirs

import icmpy


class TemplateOrigin(str, Enum):
    """Source of a discovered template."""

    BUILTIN = "built-in"
    CUSTOM = "custom"


class AmbiguousTemplateName(Exception):  # noqa: N818
    """Raised when a template name resolves to both a built-in and a custom template."""

    def __init__(self, name: str, candidates: list[Template]) -> None:
        self.name = name
        self.candidates = candidates
        origins = ", ".join(c.origin.value for c in candidates)
        msg = f"Template name '{name}' is ambiguous; found in: {origins}"
        super().__init__(msg)


@dataclass(frozen=True)
class Template:
    """A built-in or custom workspace template."""

    name: str
    description: str
    origin: TemplateOrigin
    path: Path


class TemplateCatalog:
    """Immutable catalog of built-in and custom templates.

    The catalog is snapshot at construction time; further disk changes are not
    reflected until a new catalog is built.
    """

    def __init__(
        self,
        custom_root: Path | None = None,
        *,
        builtin_root: Path | None = None,
    ) -> None:
        self._custom_root = custom_root or get_custom_template_root()
        self._builtin_root = builtin_root or Path(icmpy.__file__).parent / "templates"
        self._templates: tuple[Template, ...] = tuple(self._discover())
        by_name: dict[str, list[Template]] = {}
        for template in self._templates:
            by_name.setdefault(template.name, []).append(template)
        self._by_name: dict[str, tuple[Template, ...]] = {
            name: tuple(templates) for name, templates in by_name.items()
        }

    @property
    def warnings(self) -> tuple[str, ...]:
        return self._warnings

    @property
    def custom_root(self) -> Path:
        return self._custom_root

    @property
    def templates(self) -> tuple[Template, ...]:
        return self._templates

    def list_templates(self) -> list[dict[str, Any]]:
        """Return template entries in the legacy manifest format."""
        return [
            {"name": t.name, "description": t.description, "origin": t.origin.value}
            for t in self._templates
        ]

    def get(
        self,
        name: str,
        origin: TemplateOrigin | None = None,
    ) -> Template:
        """Return a template by name, optionally constraining its origin.

        Raises:
            AmbiguousTemplateName: when the name exists in both origins and
                no origin was requested.
            KeyError: when no template with *name* exists.
        """
        candidates = self._by_name.get(name, ())
        if not candidates:
            raise KeyError(name)

        if origin is not None:
            for candidate in candidates:
                if candidate.origin == origin:
                    return candidate
            raise KeyError(name)

        if len(candidates) > 1:
            raise AmbiguousTemplateName(name, list(candidates))
        return candidates[0]

    def is_shadowed(self, template: Template) -> bool:
        """Return True if another template shares this template's name."""
        return len(self._by_name.get(template.name, ())) > 1

    def _discover(self) -> list[Template]:
        templates: list[Template] = []
        warnings: list[str] = []
        templates.extend(self._discover_builtin(warnings))
        templates.extend(self._discover_custom(warnings))
        self._warnings = tuple(warnings)
        return templates

    def _discover_builtin(self, warnings: list[str]) -> list[Template]:  # noqa: ARG002
        import json

        root = self._builtin_root
        manifest_path = root / "builtins_manifest.json"
        if not manifest_path.is_file():
            return []

        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            warnings.append(f"Invalid built-in manifest: {exc}")
            return []

        result: list[Template] = []
        for entry in data.get("templates", []):
            name = entry.get("name", "")
            if not name:
                continue
            result.append(
                Template(
                    name=name,
                    description=entry.get("description", ""),
                    origin=TemplateOrigin.BUILTIN,
                    path=root / entry.get("path", name),
                )
            )
        return result

    def _discover_custom(self, warnings: list[str]) -> list[Template]:
        if not self._custom_root.is_dir():
            return []

        result: list[Template] = []
        for item in sorted(self._custom_root.iterdir()):
            if item.is_file():
                warnings.append(f"Ignoring loose file in custom template root: {item}")
                continue
            if not item.is_dir():
                continue

            name = item.name
            context_md = item / "CONTEXT.md"
            frontmatter: dict[str, Any] | None = None
            if context_md.is_file():
                try:
                    frontmatter = parse_frontmatter(context_md.read_text(encoding="utf-8"))
                except ValueError as exc:
                    warnings.append(f"Malformed frontmatter in {context_md}: {exc}")
                    continue

            description = ""
            if frontmatter:
                description = frontmatter.get("purpose") or frontmatter.get("description", "")
            if not description and context_md.is_file():
                description = _extract_first_heading(context_md.read_text(encoding="utf-8"))
            if not description:
                description = f"Custom template: {name}"

            result.append(
                Template(
                    name=name,
                    description=description,
                    origin=TemplateOrigin.CUSTOM,
                    path=item,
                )
            )
        return result


def get_custom_template_root() -> Path:
    """Resolve the platform-appropriate custom template directory.

    Resolution order:
      1. ``$XDG_CONFIG_HOME/icmpy/templates`` if the environment variable is set.
      2. On macOS, ``~/.config/icmpy/templates`` when ``~/.config`` already exists.
      3. ``platformdirs.user_config_dir("icmpy") / "templates"`` otherwise.
    """
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home) / "icmpy" / "templates"

    if platform.system() == "Darwin":
        dot_config = Path.home() / ".config"
        if dot_config.is_dir():
            return dot_config / "icmpy" / "templates"

    return Path(platformdirs.user_config_dir("icmpy")) / "templates"


def parse_frontmatter(text: str) -> dict[str, Any] | None:
    """Parse a basic YAML frontmatter block (delimited by ``---``)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None

    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None

    return _parse_simple_yaml(lines[1:end])


def _parse_simple_yaml(lines: list[str]) -> dict[str, Any]:
    """Parse a tiny subset of YAML sufficient for template frontmatter.

    Supports scalars (quoted or unquoted), inline lists, and indented list items.
    """
    result: dict[str, Any] = {}
    current_key: str = ""
    list_values: list[str] = []

    def flush_list() -> None:
        nonlocal current_key, list_values
        if current_key and list_values:
            result[current_key] = list_values
            current_key = ""
            list_values = []

    for raw in lines:
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue

        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        if stripped.startswith("- ") and current_key and indent > 0:
            value = stripped[2:].strip()
            list_values.append(_unquote_scalar(value))
            continue

        flush_list()

        match = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", stripped)
        if not match:
            raise ValueError(f"Unparseable frontmatter line: {line}")

        current_key = match.group(1)
        value = match.group(2).strip()

        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1]
            result[current_key] = [
                _unquote_scalar(part.strip()) for part in inner.split(",") if part.strip()
            ]
        elif value == "":
            result[current_key] = ""
        else:
            result[current_key] = _unquote_scalar(value)

        current_key = ""  # reset unless next lines are indented list items

    flush_list()
    return result


def _unquote_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


def _extract_first_heading(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return ""


def validate_custom_template(template_dir: Path) -> list[str]:
    """Validate a custom template's required CONTEXT.md frontmatter.

    Returns a list of human-readable errors; an empty list means the template
    frontmatter is well-formed. The absolute path of the offending CONTEXT.md is
    included in each error.
    """
    errors: list[str] = []
    context_md = template_dir / "CONTEXT.md"
    if not context_md.is_file():
        errors.append(f"Missing CONTEXT.md with frontmatter: {context_md}")
        return errors

    try:
        frontmatter = parse_frontmatter(context_md.read_text(encoding="utf-8"))
    except ValueError as exc:
        errors.append(f"Malformed frontmatter in {context_md}: {exc}")
        return errors

    if frontmatter is None:
        errors.append(f"Missing YAML frontmatter block in {context_md}")
        return errors

    if "purpose" not in frontmatter:
        errors.append(f"Missing required 'purpose' key in {context_md}")

    return errors
