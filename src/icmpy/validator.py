from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from icmpy.models import ContextLayer


@dataclass
class ValidationResult:
    """Result of validating an ICM workspace."""

    ok: bool
    errors: list[str] = field(default_factory=list)


def _is_stage_folder(name: str) -> bool:
    """Stage folders begin with two or more digits followed by an underscore."""
    return bool(re.match(r"^\d{2,}_[^_].*$", name))


def _extract_section(text: str, section: str) -> str | None:
    """Return the content of a markdown section heading, or None if absent."""
    pattern = rf"##\s+{re.escape(section)}\s*\n(.*?)(?:\n##\s|\Z)"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else None


def validate_workspace(workspace_path: Path) -> ValidationResult:
    """Validate that *workspace_path* conforms to ICM conventions.

    Checks:
      - Layer 0: CLAUDE.md exists
      - Layer 1: CONTEXT.md exists
      - Layer 2: stages/ exists with at least one numbered subfolder
      - Each stage folder has a CONTEXT.md with Inputs/Process/Outputs sections
      - Stage numbers are sequential with no gaps
    """
    errors: list[str] = []

    if not workspace_path.exists():
        errors.append(f"Workspace path does not exist: {workspace_path}")
        return ValidationResult(ok=False, errors=errors)

    if not workspace_path.is_dir():
        errors.append(f"Workspace path is not a directory: {workspace_path}")
        return ValidationResult(ok=False, errors=errors)

    # Layer 0
    claude_md = workspace_path / "CLAUDE.md"
    if not claude_md.is_file():
        errors.append(f"Missing Layer 0 identity file: {claude_md.relative_to(workspace_path)}")

    # Layer 1
    context_md = workspace_path / "CONTEXT.md"
    if not context_md.is_file():
        errors.append(f"Missing Layer 1 routing file: {context_md.relative_to(workspace_path)}")

    # Layer 2
    stages_dir = workspace_path / "stages"
    if not stages_dir.is_dir():
        errors.append("Missing stages/ directory (Layer 2)")
        return ValidationResult(ok=False, errors=errors)

    stage_folders = sorted(
        [p for p in stages_dir.iterdir() if p.is_dir() and _is_stage_folder(p.name)],
        key=lambda p: p.name,
    )

    if not stage_folders:
        errors.append("No numbered stage folders found under stages/")

    expected_number = 1
    for stage_folder in stage_folders:
        match = re.match(r"^(\d+)_", stage_folder.name)
        assert match is not None
        stage_number = int(match.group(1))
        if stage_number != expected_number:
            errors.append(
                f"Non-sequential stage numbering: expected {expected_number:02d}_*, "
                f"found {stage_folder.name}"
            )
        expected_number += 1

        stage_context = stage_folder / "CONTEXT.md"
        if not stage_context.is_file():
            errors.append(f"Missing stage contract: {stage_context.relative_to(workspace_path)}")
            continue

        content = stage_context.read_text(encoding="utf-8")
        required_sections = ["Inputs", "Process", "Outputs"]
        for section in required_sections:
            if _extract_section(content, section) is None:
                errors.append(
                    f"Stage {stage_folder.name} CONTEXT.md missing '## {section}' section"
                )

    is_valid = len(errors) == 0
    return ValidationResult(ok=is_valid, errors=errors)


def get_layer_file(workspace_path: Path, layer: ContextLayer) -> Path | None:
    """Return the path to the file representing an ICM layer, if it exists."""
    if layer == ContextLayer.WORKSPACE_IDENTITY:
        path = workspace_path / "CLAUDE.md"
        return path if path.is_file() else None
    if layer == ContextLayer.WORKSPACE_ROUTING:
        path = workspace_path / "CONTEXT.md"
        return path if path.is_file() else None
    return None
