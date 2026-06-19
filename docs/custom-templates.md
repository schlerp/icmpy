# Custom templates

This guide explains how to create your own `icmpy` workspace templates.

## Why templates?

Templates encode repeatable ICM workflows. They let you:

- Capture a domain-specific pipeline once
- Share it with teammates or clients as a folder
- Rebuild it with different inputs in seconds

## Template structure

A template is a folder under `src/icmpy/templates/` with this layout:

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

Use `{{ variable }}` for values. Conditional blocks and loops work as normal Jinja2.

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

## Registering the template

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

## External templates (future)

A future release will support loading templates from arbitrary folders and Git URLs via `--template-dir`.

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
icmp template cp --from empty --to my-template
```

This copies the entire template folder and adds a `CONTEXT.md` frontmatter file.
Edit the template files under the custom root as needed.

A custom template must follow the same layout as built-ins and include a
`CONTEXT.md` at its root with YAML frontmatter containing at least a `purpose`:

```markdown
---
purpose: My custom workflow template
---

# My template

Optional description of the template.
```

### Discovering and validating templates

List all available templates, including custom ones, and see any name collisions:

```bash
icmp template list
```

Validate custom templates before use:

```bash
icmp template validate
icmp template validate my-template
```

### Building from a custom template

When a custom template shares a name with a built-in, pass `--origin custom`:

```bash
icmp build create --template my-template --origin custom
```

Otherwise `icmp build create --template <name>` chooses automatically when the
name is unambiguous.
