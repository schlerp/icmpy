# Custom templates

This guide explains how to create your own `icmpy` workspace templates.

## Why templates?

Templates encode repeatable ICM workflows. They let you:

- Capture a domain-specific pipeline once
- Share it with teammates or clients as a folder
- Rebuild it with different inputs in seconds

## Template structure

A template is a folder with this layout:

```
my_template/
├── questionnaire.json
├── _config/
│   └── voice.md
└── stages/
    ├── 01_stage_one/
    │   └── CONTEXT.md
    └── 02_stage_two/
        └── CONTEXT.md
```

## questionnaire.json

This file drives `icmp build`. Each item asks one question:

```json
[
  {
    "key": "workspace_name",
    "question": "What should the workspace be named?",
    "type": "text",
    "default": "my-workspace"
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

Supported types:

| Type | Prompt behavior |
|---|---|
| `text` | Plain string prompt |
| `integer` | Integer prompt with validation |
| `confirm` | Yes/no prompt |

## Rendering files with Jinja2

Any file in the template can use questionnaire answers:

```markdown
# Voice Guide

Target length: {{ target_word_count }} words.
{% if needs_examples %}
Include a concrete example in every section.
{% endif %}
```

Use `{{ variable }}` for values. Conditional blocks and loops work as normal Jinja2:

```markdown
# Research Brief

## Context

Author: {{ author_name }}
Target length: {{ target_word_count }} words

## Requirements

{% if needs_examples %}
- Include at least one worked example per major concept
- Link to supporting material in `../_config/examples/`
{% else %}
- Keep explanations concise; assume the reader is familiar with the domain
{% endif %}
```

## Stage contracts

Each stage `CONTEXT.md` should declare:

- **Inputs** — which Layer 3 reference files and Layer 4 working artifacts to load
- **Process** — what the agent should do
- **Outputs** — what files it should write

Use relative paths:

```markdown
# Outline

## Inputs

- Layer 4 (working): `../01_research/output/research_summary.md`
- Layer 3 (reference): `../../_config/voice.md`

## Process

Turn the research summary into a section outline.

## Outputs

- `output/outline.md`
```

## Registering built-in templates

Add an entry to `src/icmpy/templates/builtins_manifest.json`:

```json
{
  "name": "my-template",
  "description": "What this template produces",
  "path": "my_template"
}
```

The `path` must match the folder name on disk.

## Testing the template

Build it locally:

```bash
icmp build --template my-template --target /tmp/test-build
```

Then validate:

```bash
icmp validate --workspace /tmp/test-build/my-workspace
```

## User-defined custom templates

`icmpy` also supports custom templates stored outside the package. Use these to
maintain team-specific or private workflows without modifying the built-in set.

### Custom template directory

Run `icmp template path` to see where custom templates live on your system. The
location follows platform conventions:

- `$XDG_CONFIG_HOME/icmpy/templates` if `XDG_CONFIG_HOME` is set.
- `~/.config/icmpy/templates` on macOS if `~/.config` exists.
- `~/Library/Application Support/icmpy/templates` on macOS otherwise.
- `~/.config/icmpy/templates` on Linux/BSD.
- `%LOCALAPPDATA%\icmpy\templates` on Windows.

Create the directory with `icmp template path --create`.

### Creating a custom template

The easiest way to start is to copy a built-in template:

```bash
# 1. Find where custom templates live on your system
icmp template path

# 2. Copy a built-in template as a starting point
icmp template cp --from empty --to blog-post

# 3. Edit the copied files under the custom template directory
```

This copies the entire template folder and adds a `CONTEXT.md` frontmatter file.
Edit the template files under the custom root as needed.

A custom template must follow the same layout as built-ins and include a
`CONTEXT.md` at its root with YAML frontmatter containing at least a `purpose`:

```markdown
---
purpose: A blog-post workflow with research, outline, draft and edit stages
---

# Blog Post Template

This template scaffolds a blog post using the ICM methodology.
```

### Full example: creating a blog-post template from scratch

Here is a complete walkthrough of creating a custom template called `blog-post`.

#### Step 1 — Set up the template directory

```bash
CUSTOM_ROOT=$(icmp template path)
mkdir -p "$CUSTOM_ROOT/blog-post/stages/01_research"
mkdir -p "$CUSTOM_ROOT/blog-post/stages/02_outline"
mkdir -p "$CUSTOM_ROOT/blog-post/stages/03_draft"
mkdir -p "$CUSTOM_ROOT/blog-post/stages/04_edit"
mkdir -p "$CUSTOM_ROOT/blog-post/_config"
```

#### Step 2 — Add the root `CONTEXT.md`

```markdown
---
purpose: A blog-post workflow with research, outline, draft and edit stages
---

# Blog Post Template

A four-stage pipeline for writing blog posts using the ICM methodology.
```

#### Step 3 — Write the questionnaire

`questionnaire.json`:

```json
[
  {
    "key": "workspace_name",
    "question": "What should the workspace be named?",
    "type": "text",
    "default": "blog-post"
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

#### Step 4 — Add stage contracts

`stages/01_research/CONTEXT.md`:

```markdown
# Research

## Inputs

- Layer 3 (reference): `../../_config/voice.md`

## Process

Research the topic thoroughly for {{ author_name }}.
Target depth: enough to support {{ target_word_count }} words.

## Outputs

- `output/research_summary.md`
```

`stages/02_outline/CONTEXT.md`:

```markdown
# Outline

## Inputs

- Layer 4 (working): `../01_research/output/research_summary.md`
- Layer 3 (reference): `../../_config/voice.md`

## Process

Turn the research summary into a structured outline.

## Outputs

- `output/outline.md`
```

`stages/03_draft/CONTEXT.md`:

```markdown
# Draft

## Inputs

- Layer 4 (working): `../02_outline/output/outline.md`
- Layer 3 (reference): `../../_config/voice.md`

## Process

Write the first draft following the outline.

{% if needs_examples %}
Include a concrete example in every major section.
{% endif %}

## Outputs

- `output/draft.md`
```

`stages/04_edit/CONTEXT.md`:

```markdown
# Edit

## Inputs

- Layer 4 (working): `../03_draft/output/draft.md`
- Layer 3 (reference): `../../_config/voice.md`

## Process

Edit the draft for clarity, flow, and length. Target {{ target_word_count }} words.

## Outputs

- `output/final.md`
```

#### Step 5 — Add reference material

`_config/voice.md`:

```markdown
# Voice Guide

Author: {{ author_name }}
Tone: Conversational but informative.
Audience: Technical readers with some domain knowledge.
```

#### Step 6 — Build and test

```bash
# List templates to confirm it appears
icmp template list

# Validate the template
icmp template validate blog-post

# Build a workspace from it
icmp build create --template blog-post --target /tmp/test-blog
```

### Discovering and validating templates

List all available templates, including custom ones, and see any name collisions:

```bash
icmp template list
```

Validate custom templates before use:

```bash
icmp template validate
icmp template validate blog-post
```

### Building from a custom template

When a custom template shares a name with a built-in, pass `--origin custom`:

```bash
icmp build create --template my-template --origin custom
```

Otherwise `icmp build create --template <name>` chooses automatically when the
name is unambiguous.

Skip interactive prompts with a JSON answers file:

```bash
icmp build create --template blog-post --answers-file answers.json
```

An `answers.json` file looks like this:

```json
{
  "workspace_name": "kubernetes-operators-post",
  "author_name": "Jane Doe",
  "target_word_count": 2000,
  "needs_examples": true
}
```

## External templates (future)

A future release will support loading templates from arbitrary folders and Git URLs via `--template-dir`.
