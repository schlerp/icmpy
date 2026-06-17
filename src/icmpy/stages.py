from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from icmpy.validator import _extract_section


@dataclass
class StageInfo:
    """Lightweight summary of an ICM stage for listing and lookup."""

    number: int
    directory: str
    name: str
    status: str
    inputs: list[str]
    outputs: list[str]
    path: Path


def _is_stage_folder(name: str) -> bool:
    return bool(re.match(r"^\d{2,}_[^_].*$", name))


def _parse_stage_contract(stage_dir: Path) -> dict[str, list[str]]:
    """Read a stage CONTEXT.md and return its Inputs / Outputs as string lists."""
    contract_path = stage_dir / "CONTEXT.md"
    if not contract_path.is_file():
        return {"inputs": [], "outputs": []}
    content = contract_path.read_text(encoding="utf-8")

    def _clean_bullets(section: str | None) -> list[str]:
        if section is None:
            return []
        lines = [line.strip() for line in section.splitlines() if line.strip()]
        lines = [line.lstrip("-").strip() for line in lines]
        return [line for line in lines if line]

    return {
        "inputs": _clean_bullets(_extract_section(content, "Inputs")),
        "outputs": _clean_bullets(_extract_section(content, "Outputs")),
    }


def discover_stages(workspace_path: Path) -> list[StageInfo]:
    """Return all numbered stages in *workspace_path*, sorted by stage number."""
    stages_dir = workspace_path / "stages"
    if not stages_dir.is_dir():
        return []

    stage_dirs = sorted(
        [p for p in stages_dir.iterdir() if p.is_dir() and _is_stage_folder(p.name)],
        key=lambda p: p.name,
    )

    result: list[StageInfo] = []
    for stage_dir in stage_dirs:
        match = re.match(r"^(\d+)_", stage_dir.name)
        if not match:
            continue
        number = int(match.group(1))
        title = stage_dir.name.split("_", 1)[1].replace("_", " ").title()
        contract = _parse_stage_contract(stage_dir)
        output_dir = stage_dir / "output"
        status = "completed" if output_dir.is_dir() and any(output_dir.iterdir()) else "pending"
        result.append(
            StageInfo(
                number=number,
                directory=stage_dir.name,
                name=title,
                status=status,
                inputs=contract["inputs"],
                outputs=contract["outputs"],
                path=stage_dir,
            )
        )

    return result


def next_pending_stage(workspace_path: Path) -> StageInfo | None:
    """Return the first numbered stage with no populated output directory."""
    for stage in discover_stages(workspace_path):
        if stage.status == "pending":
            return stage
    return None


def find_stage(workspace_path: Path, identifier: str) -> StageInfo | None:
    """Find a stage by number (e.g. '01') or by directory name (e.g. '01_research')."""
    stages = discover_stages(workspace_path)

    # Exact directory name match
    for stage in stages:
        if stage.directory == identifier:
            return stage

    # Number prefix match
    prefix = identifier
    if not prefix.startswith("0") and prefix.isdigit():
        prefix = f"{int(prefix):02d}"
    for stage in stages:
        if f"{stage.number:02d}" == prefix:
            return stage

    # Partial name match
    for stage in stages:
        if identifier.lower() in stage.name.lower():
            return stage

    return None
