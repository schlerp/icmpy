from __future__ import annotations

from pathlib import Path
from typing import Any

from icmpy.models import ContextLayer
from icmpy.stages import find_stage


def _read_file_if_exists(path: Path) -> str | None:
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return None


def _resolve_input_path(workspace_path: Path, stage_dir: Path, input_path: str, layer: int) -> Path:
    """Resolve a relative path from a stage contract to an absolute path.

    Layer 3 (reference) paths are relative to the workspace root.
    Layer 4 (working) paths beginning with ../ resolve relative to the stage
    directory; otherwise they are relative to the stage directory.
    """
    raw = Path(input_path)
    if layer == 3:
        return workspace_path / raw
    if raw.parts[0] == "..":
        return (stage_dir / raw).resolve()
    return stage_dir / raw


def assemble_context_bundle(
    workspace_path: Path,
    stage_identifier: str,
) -> dict[str, Any]:
    """Assemble the full context bundle for a stage.

    Returns a dict with separate keys for Layers 0-4 plus metadata:
        - layer_0_identity: str
        - layer_1_routing: str
        - layer_2_contract: str
        - layer_3_reference: list[(file_path, content)]
        - layer_4_working: list[(file_path, content)]
        - stage_name: str
        - stage_dir: Path
    """
    stage = find_stage(workspace_path, stage_identifier)
    if stage is None:
        msg = f"Stage not found: {stage_identifier}"
        raise ValueError(msg)

    stage_dir = workspace_path / "stages" / stage.directory

    layer_0 = _read_file_if_exists(workspace_path / "CLAUDE.md")
    layer_1 = _read_file_if_exists(workspace_path / "CONTEXT.md")
    layer_2 = _read_file_if_exists(stage_dir / "CONTEXT.md")

    layer_3: list[tuple[str, str | None]] = []
    layer_4: list[tuple[str, str | None]] = []

    contract = layer_2 or ""
    for line in contract.splitlines():
        stripped = line.strip()
        if not stripped.startswith("-"):
            continue
        item = stripped.lstrip("-").strip()

        if item.startswith("Layer 3") or item.startswith("Layer 4"):
            # Parse optional inline prefix notation used in templates
            parts = item.split(":", 1)
            if len(parts) == 2:
                layer_label = parts[0].strip()
                path_value = parts[1].strip().strip("`")
                layer = 3 if "3" in layer_label else 4
                resolved = _resolve_input_path(workspace_path, stage_dir, path_value, layer)
                content = _read_file_if_exists(resolved)
                rel = str(resolved.relative_to(workspace_path))
                if layer == 3:
                    layer_3.append((rel, content))
                else:
                    layer_4.append((rel, content))

    return {
        "layer_0_identity": layer_0 or "",
        "layer_1_routing": layer_1 or "",
        "layer_2_contract": layer_2 or "",
        "layer_3_reference": layer_3,
        "layer_4_working": layer_4,
        "stage_name": stage.name,
        "stage_dir": stage_dir,
    }


def render_context_bundle(bundle: dict[str, Any]) -> str:
    """Render a context bundle as a single plain-text prompt."""
    parts: list[str] = []

    def _add(heading: str, content: str) -> None:
        parts.append(f"=== {heading} ===")
        parts.append(content)
        parts.append("")

    if bundle["layer_0_identity"]:
        _add(f"Layer {ContextLayer.WORKSPACE_IDENTITY} (Workspace Identity)", bundle["layer_0_identity"])
    if bundle["layer_1_routing"]:
        _add(f"Layer {ContextLayer.WORKSPACE_ROUTING} (Workspace Routing)", bundle["layer_1_routing"])
    if bundle["layer_2_contract"]:
        _add(
            f"Layer {ContextLayer.STAGE_CONTRACT} (Stage Contract: {bundle['stage_name']})",
            bundle["layer_2_contract"],
        )

    if bundle["layer_3_reference"]:
        parts.append(f"=== Layer {ContextLayer.REFERENCE_MATERIAL} (Reference Material) ===")
        for path, content in bundle["layer_3_reference"]:
            parts.append(f"--- file: {path} ---")
            parts.append(content if content is not None else "[file not found]")
            parts.append("")

    if bundle["layer_4_working"]:
        parts.append(f"=== Layer {ContextLayer.WORKING_ARTIFACTS} (Working Artifacts) ===")
        for path, content in bundle["layer_4_working"]:
            parts.append(f"--- file: {path} ---")
            parts.append(content if content is not None else "[file not found]")
            parts.append("")

    return "\n".join(parts).strip()
