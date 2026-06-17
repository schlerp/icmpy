# icmpy

A command-line scaffolding and orchestration tool for the [Interpretable Context Methodology](https://arxiv.org/abs/2603.16021) (ICM).

ICM treats folder structure as agent architecture: numbered stage folders carry prompts as plain markdown files, reference material lives in `_config/`, and working artifacts move through `output/` directories. The result is a sequential, reviewable, human-in-the-loop AI workflow that needs no multi-agent framework.

**icmpy** automates the boring parts: creating workspaces, validating structure, building from templates, assembling stage-specific context bundles, and tracking progress.

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
uv sync
source .venv/bin/activate
```

Run checks with `uv run`:

```bash
uv run pytest
uv run ruff check src/ tests/
uv run mypy src/
```

## Quickstart

Create and validate a workspace:

```bash
icmp init my-workspace
cd my-workspace
icmp validate
```

Build a ready-made workspace from a template:

```bash
icmp build create --template long-form-essay
```

Run the first pending stage:

```bash
cd long-form-essay
icmp stage run next
```

This prints the assembled context bundle (Layers 0-4) for your agent. Review the output, then save the agent's response to the stage's `output/` directory before running the next stage.

## Core workflow

1. **Scaffold or build** a workspace.
2. **Review and edit** the generated `CONTEXT.md` contracts and `_config/` reference files.
3. **Run a stage** to get a focused context bundle.
4. **Paste the bundle** into your AI tool and capture its output.
5. **Save the output** to the stage's `output/` folder.
6. Repeat from step 3 for the next stage.

## Built-in templates

Build a complete workspace from a template:

```bash
icmp build create --template script-to-animation
```

List available templates:

```bash
icmp build list
```

Preview a template before building:

```bash
icmp build info feature-spec
```

This shows the template description, questionnaire questions, and stage pipeline.

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
| `literature-review` | Search → Extraction → Synthesis → Themes → Draft |
| `competitive-analysis` | Competitors → Feature Grid → Positioning → Strategy Brief |
| `landing-page` | Value Prop → Outline → Copy → Design Brief → Launch Checklist |
| `campaign-brief` | Objective → Audience → Messaging → Channel Plan |
| `client-onboarding` | Discovery → Playbook → Assets → Launch Checklist |

Templates are Jinja2-rendered and come with their own builder questionnaire. Use `--answers-file` to skip interactive prompts:

```bash
icmp build --template landing-page --answers-file answers.json
```

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
| `icmp status` | Show workspace health and progress |
| `icmp build create --template <name>` | Build a workspace from a built-in template |
| `icmp build create --answers-file <path>` | Build non-interactively from JSON answers |
| `icmp build list` | List available templates |
| `icmp build info <template>` | Preview a template's questions and stages |
| `icmp stage list` | List stages with status |
| `icmp stage run <stage>` | Assemble and print a stage's context bundle |
| `icmp stage run next` | Run the first pending stage |
| `icmp completion <bash|zsh|fish>` | Print shell completion script |
| `icmp --version` | Show version |

Global flags:

- `--dry-run` — show what would happen without writing files
- `-V` / `--verbose` — increase verbosity

## Context bundles

A context bundle is the plain-text prompt that `icmp stage run` assembles for the current stage. It includes:

- Layer 0: workspace identity (`CLAUDE.md`)
- Layer 1: workspace routing (`CONTEXT.md`)
- Layer 2: stage contract (`stages/NN_name/CONTEXT.md`)
- Layer 3: reference material from `_config/` or stage `references/`
- Layer 4: working artifacts from previous `output/` directories

The bundle is rendered as markdown with `# Layer N` headings and `## file:` markers, so it is easy to read and paste into any AI tool.

If the estimated token count exceeds 8,000, `icmp` prints a warning because model performance tends to degrade with very long contexts.

## Writing your own template

Templates live under `src/icmpy/templates/` and contain:

- `questionnaire.json` — questions asked during `icmp build`
- `_config/voice.md` — template-specific reference material
- `stages/NN_name/CONTEXT.md` — stage contracts

Use Jinja2 syntax (`{{ variable }}`) to substitute questionnaire answers into any file. Add the template to `builtins_manifest.json` to make it discoverable.

See `docs/custom-templates.md` for a full guide.

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

## Contributing

See `CONTRIBUTING.md`.

## License

MIT. See `LICENSE` for details.
