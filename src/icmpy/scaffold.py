from __future__ import annotations

from pathlib import Path


CLAUDE_MD_TEMPLATE = """# {name} — ICM Workspace

This is an [Interpretable Context Methodology](https://github.com/eduba/icmpy) (ICM) workspace.

## Structure

- `CONTEXT.md` — Workspace-level routing (Layer 1)
- `stages/` — Numbered stage folders, each with its own `CONTEXT.md` contract (Layer 2)
- `_config/` — Shared reference material such as voice, style, and conventions (Layer 3)
- Each stage's `output/` directory holds working artifacts produced and consumed during runs (Layer 4)

## Usage

1. Define stages in `stages/01_<name>/`, `stages/02_<name>/`, etc.
2. Every stage folder contains a `CONTEXT.md` with an Inputs / Process / Outputs contract.
3. Place stable reference material in `_config/`.
4. Run a stage with: `icmp stage run <stage>`
"""


CONTEXT_MD_TEMPLATE = """# {name} — Workspace Routing

## Purpose

<!-- Describe what this workspace produces. -->

## Stages

<!-- List the numbered stages below. The orchestrating agent uses this file to route tasks. -->

### 01 — Research

Takes source material and produces structured research output.

### 02 — Production

Transforms the research output into the final deliverable.

## Shared Resources

<!-- Reference files in `_config/` that apply across multiple stages. -->

- `_config/voice.md` — Voice and tone guide
"""


VOICE_MD_TEMPLATE = """# Voice Guide

## Tone
Professional yet approachable.

## Style
- Clear, concise sentences
- Use bullet points for lists
- Prefer active voice

## Conventions
- Markdown headings for sections
- Include a brief summary at the end of each stage output
"""


def create_workspace(target: Path) -> None:
    """Create an empty ICM workspace scaffold at *target*.

    Does not create numbered stage folders — those are added later by the user
    or by `icmp build`.
    """
    if target.exists():
        msg = f"Workspace already exists: {target}"
        raise FileExistsError(msg)

    target.mkdir(parents=True)
    config_dir = target / "_config"
    stages_dir = target / "stages"
    config_dir.mkdir()
    stages_dir.mkdir()

    name = target.name

    (target / "CLAUDE.md").write_text(CLAUDE_MD_TEMPLATE.format(name=name), encoding="utf-8")
    (target / "CONTEXT.md").write_text(CONTEXT_MD_TEMPLATE.format(name=name), encoding="utf-8")
    (config_dir / "voice.md").write_text(VOICE_MD_TEMPLATE, encoding="utf-8")
