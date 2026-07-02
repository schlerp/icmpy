from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


class HarnessError(Exception):
    """Raised when a harness cannot be resolved or executed."""


@dataclass(frozen=True)
class HarnessAdapter:
    """Description of how to hand a rendered context bundle to an LLM harness."""

    name: str
    command: list[str]
    input_mode: Literal["stdin", "file_arg", "file_in_prompt"]
    prompt: str = "Execute the attached ICM stage contract and produce the requested outputs."

    def build_command(self, bundle_file: Path) -> list[str]:
        """Return the concrete command list, substituting placeholders."""
        rendered_prompt = self.prompt.replace("{file}", str(bundle_file))
        return [
            part.replace("{prompt}", rendered_prompt).replace("{file}", str(bundle_file))
            for part in self.command
        ]


# Built-in adapters for common autonomous coding / LLM harness CLIs.
# These are intentionally conservative: non-interactive, bounded turn counts where
# supported, and they pass the assembled ICM bundle as the primary prompt context.
BUILTIN_HARNESSES: dict[str, HarnessAdapter] = {
    "claude": HarnessAdapter(
        name="claude",
        command=["claude", "-p", "{prompt}", "--max-turns", "10"],
        input_mode="stdin",
        prompt=(
            "Execute the attached ICM stage contract and produce the requested outputs. "
            "The full stage context (Layers 0-4) is supplied via stdin."
        ),
    ),
    "codex": HarnessAdapter(
        name="codex",
        command=["codex", "exec", "{prompt}"],
        input_mode="file_in_prompt",
        prompt=(
            "Execute the ICM stage contract in {file} and produce the requested outputs. "
            "Read the full stage context (Layers 0-4) from that file."
        ),
    ),
    "opencode": HarnessAdapter(
        name="opencode",
        command=["opencode", "run", "{prompt}", "-f", "{file}"],
        input_mode="file_arg",
        prompt=(
            "Execute the attached ICM stage contract and produce the requested outputs. "
            "The full stage context (Layers 0-4) is attached as a file."
        ),
    ),
    "pi": HarnessAdapter(
        name="pi",
        command=["pi", "-p", "{prompt}", "@{file}"],
        input_mode="file_arg",
        prompt=(
            "Execute the attached ICM stage contract and produce the requested outputs. "
            "The full stage context (Layers 0-4) is included as an attachment."
        ),
    ),
}


def list_harnesses() -> list[str]:
    """Return the names of available built-in harness adapters."""
    return sorted(BUILTIN_HARNESSES.keys())


def get_harness(name: str) -> HarnessAdapter:
    """Resolve a harness name to its adapter.

    Raises:
        HarnessError: if the harness is unknown.
    """
    try:
        return BUILTIN_HARNESSES[name]
    except KeyError as exc:
        available = ", ".join(list_harnesses())
        msg = f"Unknown harness '{name}'. Available: {available}"
        raise HarnessError(msg) from exc


def write_bundle_file(stage_dir: Path, bundle_text: str) -> Path:
    """Write *bundle_text* to a temporary markdown file inside *stage_dir*.

    If the stage has an ``output/`` directory, the bundle is written there so
    the exact prompt dispatched to the harness is preserved alongside the
    harness response.
    """
    output_dir = stage_dir / "output"
    target_dir = output_dir if output_dir.is_dir() else stage_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".md",
        prefix="harness_bundle_",
        dir=target_dir,
        delete=False,
    ) as handle:
        handle.write(bundle_text)
        return Path(handle.name)


def run_harness(
    name: str,
    bundle_text: str,
    *,
    workspace_path: Path,
    stage_dir: Path,
    dry_run: bool = False,
) -> tuple[str, list[str]]:
    """Dispatch *bundle_text* to the named harness and return captured output.

    Args:
        name: Harness name (e.g. ``claude``, ``codex``, ``opencode``).
        bundle_text: Rendered context bundle for the stage.
        workspace_path: Working directory for the harness subprocess.
        stage_dir: Stage directory used to store the temporary bundle file.
        dry_run: If True, build and return the command without executing it.

    Returns:
        A tuple of ``(stdout_or_dry_run_message, command_list)``.

    Raises:
        HarnessError: if the harness is unknown, missing, or exits non-zero.
    """
    adapter = get_harness(name)
    bundle_file = write_bundle_file(stage_dir, bundle_text)
    command = adapter.build_command(bundle_file)

    if dry_run:
        return (
            f"[dry-run] Would run: {' '.join(command)}\n[dry-run] Bundle file: {bundle_file}"
        ), command

    if shutil.which(command[0]) is None:
        msg = (
            f"Harness command '{command[0]}' not found on PATH. "
            f"Install the {adapter.name} CLI and try again."
        )
        raise HarnessError(msg)

    input_data: str | None = None
    if adapter.input_mode == "stdin":
        input_data = bundle_text

    try:
        result = subprocess.run(
            command,
            cwd=workspace_path,
            input=input_data,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        msg = f"Failed to start harness '{adapter.name}': {exc}"
        raise HarnessError(msg) from exc

    if result.returncode != 0:
        stderr = result.stderr.strip()
        msg = f"Harness '{adapter.name}' exited with code {result.returncode}"
        if stderr:
            msg += f": {stderr}"
        raise HarnessError(msg)

    return result.stdout, command
