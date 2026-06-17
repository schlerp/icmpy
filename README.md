# icmpy

A command-line scaffolding and orchestration tool for the [Interpretable Context Methodology](https://arxiv.org/abs/2603.16021) (ICM).

ICM treats folder structure as agent architecture: numbered stage folders carry prompts as plain markdown files, reference material lives in `_config/`, and working artifacts move through `output/` directories. The result is a sequential, reviewable, human-in-the-loop AI workflow that needs no multi-agent framework.

**icmpy** automates the boring parts: creating workspaces, validating structure, building from templates, and assembling stage-specific context bundles for the orchestrating agent.

## Installation

```bash
pip install icmpy
# or
uv pip install icmpy
```

For local development:

```bash
git clone https://github.com/eduba/icmpy.git
cd icmpy
uv sync --extra dev
source .venv/bin/activate
```

## Quickstart

Create and validate a workspace:

```bash
icmp init my-workspace
cd my-workspace
icmp validate
```

Add a stage by hand:

```bash
mkdir -p stages/01_research/output
cat > stages/01_research/CONTEXT.md <<'EOF'
# Research

## Inputs

- Layer 4 (working): `output/topic_brief.md`

## Process

Analyze the topic brief and produce a structured research summary.

## Outputs

- `output/research_summary.md`
EOF
```

Run the stage:

```bash
icmp stage run 01
```

This prints the assembled context bundle (Layers 0-4) for your agent. You can also write it to a file:

```bash
icmp stage run 01 -o bundle.md
```

## Built-in templates

Build a complete workspace from a template:

```bash
icmp build --template script-to-animation
```

Available templates:

| Template | Description |
|---|---|
| `empty` | Minimal ICM scaffold with no stages |
| `script-to-animation` | Research → Script → Production |
| `long-form-essay` | Idea → Research → Outline → Draft → Edit |
| `course-module` | Learning design → Outline → Content → Slides → Assessment |
| `weekly-report` | Data → Highlights → Narrative → Review |
| `feature-spec` | Problem → Requirements → UX Flow → API Spec → PRD |
| `bug-runbook` | Reproduction → Root Cause → Fix → Validation → Post Mortem |
| `api-design` | Use Cases → Endpoints → Schemas → Examples → Documentation |

Templates are Jinja2-rendered and come with their own builder questionnaire.

## Workspace structure

```
my-workspace/
├── CLAUDE.md          # Layer 0: workspace identity
├── CONTEXT.md         # Layer 1: workspace routing
├── _config/           # Layer 3: reference material
│   └── voice.md
└── stages/            # Layer 2: stage contracts
    ├── 01_research/
    │   ├── CONTEXT.md
    │   └── output/    # Layer 4: working artifacts
    └── 02_script/
        ├── CONTEXT.md
        └── output/
```

## Commands

| Command | Description |
|---|---|
| `icmp init <name>` | Scaffold a new ICM workspace |
| `icmp validate` | Validate the current workspace structure |
| `icmp build --template <name>` | Build a workspace from a built-in template |
| `icmp stage list` | List stages with status |
| `icmp stage run <stage>` | Assemble and print a stage's context bundle |
| `icmp --version` | Show version |

Global flags:

- `--dry-run` — show what would happen without writing files
- `-V` / `--verbose` — increase verbosity

## Development

Run tests:

```bash
pytest
```

Lint and type-check:

```bash
ruff check src/ tests/
ruff format --check src/ tests/
mypy src/
```

## License

MIT. See `LICENSE` for details.
