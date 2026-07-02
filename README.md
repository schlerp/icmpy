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
| `icmp stage run <stage> --harness <name>` | Dispatch a stage's bundle to an LLM harness |
| `icmp stage run next` | Run the first pending stage |
| `icmp harness list` | List available LLM harness adapters |
| `icmp reset` | Clear run flags for all stages (makes them pending) |
| `icmp reset <stage>` | Clear the run flag for a single stage |
| `icmp reset --remove-outputs` | Also delete stage `output/` directories |
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

## Running stages through LLM harnesses

Instead of copying and pasting the bundle, you can dispatch it straight to a supported LLM harness:

```bash
# Run the next pending stage through Claude Code
icmp stage run next --harness claude

# Use OpenAI Codex, OpenCode, or pi
icmp stage run 01 --harness codex
icmp stage run 02 --harness opencode
icmp stage run 03 --harness pi
```

The harness receives the full context bundle (Layers 0-4) and its response is saved to the stage's `output/` directory as `<harness>.md`. The stage is marked complete so `next` can continue.

List available harness adapters:

```bash
icmp harness list
```

Dry-run a harness dispatch to see the command that would be executed:

```bash
icmp --dry-run stage run next --harness claude
```

## Writing your own template

You can create templates locally without touching the package source. The fastest way is to copy a built-in template and edit it:

```bash
# 1. Find where custom templates live on your system
icmp template path

# 2. Copy a built-in template as a starting point
icmp template cp --from empty --to blog-post

# 3. Edit the copied files under the custom template directory
```

Add a root `CONTEXT.md` to the template with YAML frontmatter so `icmpy` knows what it is:

```markdown
---
purpose: A blog-post workflow with research, outline, draft and edit stages
---
```

### Questionnaire example

The `questionnaire.json` drives the interactive prompts when building:

```json
[
  {
    "key": "workspace_name",
    "question": "What should the workspace be named?",
    "type": "text",
    "default": "my-icm-workspace"
  },
  {
    "key": "author_name",
    "question": "Who is the author?",
    "type": "text",
    "default": "Anonymous"
  },
  {
    "key": "target_word_count",
    "question": "Target word count?",
    "type": "integer",
    "default": 1200
  },
  {
    "key": "needs_examples",
    "question": "Include worked examples?",
    "type": "confirm",
    "default": true
  }
]
```

### Jinja2 rendering

Any template file can use questionnaire answers:

```markdown
# Blog Post - Research Stage

## Inputs

{% if needs_examples %}
- Example posts from _config/examples/
{% endif %}

## Process

Research topic for {{ author_name }}.
Target length: {{ target_word_count }} words.
```

### Building from a custom template

When a custom template shares a name with a built-in, pass `--origin custom`:

```bash
icmp build create --template blog-post --origin custom
```

Skip interactive prompts with a JSON answers file:

```bash
icmp build create --template blog-post --answers-file answers.json
```

List and validate your custom templates:

```bash
icmp template list
icmp template validate blog-post
```

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
