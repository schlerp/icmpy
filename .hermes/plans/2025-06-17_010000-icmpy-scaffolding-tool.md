# icmpy Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.
>
> **Skill to load when implementing:** `test-driven-development`

**Goal:** Build `icmpy` — a CLI scaffolding and orchestration tool for the Interpretable Context Methodology (ICM). It creates workspaces from templates, validates workspace structure, and can execute stages sequentially with human review gates.

**Architecture:** A Python CLI package built with `typer`, using `pydantic` for configuration validation, and `jinja2` for template rendering. The tool follows the ICM conventions defined in the paper and provides commands for workspace scaffolding (`init`, `validate`, `stage run`, `build`), a workspace-builder template engine, and a stage execution runner.

**Tech Stack:** Python 3.12+, typer, pydantic, jinja2, pytest, ruff, mypy

---

## Current State

- Empty Python package at `src/icmpy/` with a stub `hello()` function and an incomplete `setup_icm_workspace()` helper.
- `pyproject.toml` configured with hatchling, no dependencies.
- `README.md` is empty.
- No tests, no CLI entry point, no validation logic.

---

## Phase 1: Project Infrastructure & Tooling

### Task 1: Add dependencies and dev dependencies to pyproject.toml

**Objective:** Configure the build system with all required runtime and dev dependencies.

**Files:**
- Modify: `pyproject.toml`

**Changes:**
- Add `dependencies = ["typer>=0.12", "pydantic>=2.0", "jinja2>=3.1", "rich>=13.0"]'
- Add `[project.optional-dependencies] dev = ["pytest>=8.0", "pytest-cov", "ruff>=0.6", "mypy>=1.0"]`
- Add `[project.scripts] icmp = "icmpy.cli:app"`
- Add `[tool.ruff]`, `[tool.ruff.lint]`, `[tool.mypy]` configurations

**Verification:** `uv pip install -e ".[dev]"` (or `pip install -e ".[dev]"`) succeeds.

**Commit:** `git add pyproject.toml && git commit -m "chore: add deps and tooling config"`

---

### Task 2: Set up test infrastructure

**Objective:** Create a pytest configuration and the tests directory structure.

**Files:**
- Create: `pyproject.toml` (add `[tool.pytest.ini_options]`)
- Create: `tests/__init__.py`
- Create: `tests/conftest.py` with a `tmp_workspace` fixture that creates a temporary directory

**Verification:** Run `pytest tests/` — should discover zero tests and exit 0.

**Commit:** `git add tests/ pyproject.toml && git commit -m "chore: test infrastructure"`

---

### Task 3: Configure CI with GitHub Actions

**Objective:** Add a workflow that runs ruff, mypy, and pytest on push/PR.

**Files:**
- Create: `.github/workflows/ci.yml`

**Content:** Standard Python CI matrix for 3.12, runs `ruff check .`, `ruff format --check .`, `mypy src/`, `pytest -v --cov=icmpy --cov-report=term-missing`.

**Verification:** Push to a branch, open a PR, confirm CI passes.

**Commit:** `git add .github/workflows/ci.yml && git commit -m "ci: github actions workflow"`

---

## Phase 2: Core Data Models & Validation

### Task 4: Define Pydantic models for ICM workspace structure

**Objective:** Model the five-layer context hierarchy and stage contracts so we can validate any workspace folder against the ICM schema.

**Files:**
- Create: `src/icmpy/models.py`

**Models to implement:**

```python
class StageInput(BaseModel):
    layer: Literal[3, 4]
    path: str   # relative path within workspace
    sections: list[str] | None = None

class StageContract(BaseModel):
    name: str
    inputs: list[StageInput]
    process: str
    outputs: list[str]  # relative paths within stage dir

class WorkspaceConfig(BaseModel):
    name: str
    version: str = "1.0.0"
    description: str = ""
    stages: list[StageContract]
```

Also define a `Layer` enum and `WorkspaceLayer` model for the five-layer hierarchy.

**Verification:** `python -c "from icmpy.models import WorkspaceConfig; print('ok')"`

**Commit:** `git add src/icmpy/models.py && git commit -m "feat: core pydantic models for ICM workspace"`

---

### Task 5: Workspace validation engine

**Objective:** Implement a `validate_workspace(path: Path)` function that checks a directory against ICM conventions.

**Files:**
- Create: `src/icmpy/validator.py`

**Checks to implement (in order):**
1. `CLAUDE.md` exists at the root (Layer 0)
2. `CONTEXT.md` exists at the root (Layer 1)
3. `stages/` directory exists with at least one numbered folder (Layer 2)
4. Each stage folder has:
   - A `CONTEXT.md` file with parsable Inputs/Process/Outputs sections
   - Optionally `references/` and `output/` subdirectories
5. `_config/` or `references/` directories are valid reference locations (Layer 3)
6. Stage numbers are sequential (01, 02, 03...) with no gaps

Return a `ValidationResult` dataclass with `.ok: bool` and `.errors: list[str]`.

**Verification:**
- Write a test in `tests/test_validator.py` that creates a valid workspace and asserts `ok=True`.
- Write a test that creates an invalid workspace (missing CONTEXT.md) and asserts `ok=False` with the expected error.

**Commit:** `git add src/icmpy/validator.py tests/test_validator.py && git commit -m "feat: workspace validation engine"`

---

## Phase 3: CLI Commands

### Task 6: Scaffold the CLI entry point with typer

**Objective:** Create the main CLI app with subcommands and rich output.

**Files:**
- Create: `src/icmpy/cli.py`

**Commands to register:**
- `icmp init <workspace_name>` — scaffold a new ICM workspace
- `icmp validate [workspace_path]` — validate an existing workspace
- `icmp build` — run the workspace-builder to create a new workspace from questionnaire
- `icmp stage run <stage_name_or_number>` — execute a single stage
- `icmp stage list` — list stages in the current workspace

Use `typer` with rich `Console()` for colored output. Add `--version` flag.

**Verification:** `python -m icmpy.cli --help` shows all commands.

**Commit:** `git add src/icmpy/cli.py && git commit -m "feat: cli entry point with typer"`

---

### Task 7: Implement `icmp init <name>`

**Objective:** Replace the stub `setup_icm_workspace()` with a proper `init` command.

**Files:**
- Create: `src/icmpy/scaffold.py`
- Modify: `src/icmpy/__init__.py` (remove old `setup_icm_workspace`)

**Behavior:**
- Create `<name>/` directory
- Create Layer 0: `CLAUDE.md` with a template explaining the workspace identity
- Create Layer 1: `CONTEXT.md` with a routing template
- Create `stages/` directory
- Create `_config/` directory with sample `voice.md`
- Do NOT create numbered stage folders — those come from `build` or manual creation

**CLAUDE.md template content:**
```markdown
# {workspace_name} — ICM Workspace

This is an Interpretable Context Methodology workspace.

## Structure
- `CONTEXT.md` — Workspace-level routing (Layer 1)
- `stages/` — Numbered stage folders (Layer 2)
- `_config/` — Reference material shared across stages (Layer 3)
- Each stage's `output/` folder holds working artifacts (Layer 4)

## Usage
1. Define stages in `stages/01_<name>/`, `stages/02_<name>/`, etc.
2. Each stage contains a `CONTEXT.md` with its contract.
3. Run stages with: `icmp stage run <stage>`
```

**Context.md template:**
```markdown
# {workspace_name} — Context

## Stages
<!-- List stages here. The orchestrating agent reads this to route tasks. -->

## Shared Resources
<!-- Reference files in _config/ that apply across stages -->
```

**Verification:**
- Test: `icmp init test_ws` creates a valid workspace
- Then: `icmp validate test_ws` passes

**Commit:** `git add src/icmpy/scaffold.py src/icmpy/__init__.py tests/test_scaffold.py && git commit -m "feat: init command scaffolds ICM workspace"`

---

### Task 8: Implement `icmp validate [path]`

**Objective:** Wire the validation engine into the CLI.

**Files:**
- Modify: `src/icmpy/cli.py`

**Behavior:**
- Default `path` is current working directory
- Call `validate_workspace(path)`
- If ok: print green "Workspace is valid ICM structure"
- If not ok: print red "Workspace validation failed" followed by each error
- Exit code 0 on success, 1 on failure

**Verification:**
- `icmp validate` in a valid workspace exits 0
- `icmp validate` in an invalid directory exits 1 with readable errors

**Commit:** `git add src/icmpy/cli.py tests/test_cli_validate.py && git commit -m "feat: validate command wired to validator"`

---

## Phase 4: Workspace Builder (Template Engine)

### Task 9: Design the workspace-builder template format

**Objective:** Define how built-in workspace templates are stored and rendered.

**Files:**
- Create: `src/icmpy/templates/` directory
- Create: `src/icmpy/templates/builtins_manifest.json`

**Manifest schema:**
```json
{
  "templates": [
    {
      "name": "script-to-animation",
      "description": "Three-stage pipeline: research → script → production",
      "path": "script_to_animation"
    },
    {
      "name": "slide-deck",
      "description": "Five-stage pipeline for course deck production",
      "path": "slide_deck"
    }
  ]
}
```

Each template directory contains:
- `stages/` with numbered folders, each containing `CONTEXT.md` and optionally `references/`
- `_config/` with shared reference material
- `questionnaire.json` — a list of questions to ask the user during `icmp build`

**Verification:** `python -c "import json; json.load(open('src/icmpy/templates/builtins_manifest.json'))"`

**Commit:** `git add src/icmpy/templates/ && git commit -m "feat: workspace-builder template manifest"`

---

### Task 10: Implement `icmp build` — workspace builder

**Objective:** Allow users to create a domain-specific workspace by answering a questionnaire.

**Files:**
- Create: `src/icmpy/builder.py`

**Behavior:**
1. List available templates from the manifest
2. User selects a template (interactive prompt or `--template <name>`)
3. Load the template's `questionnaire.json`
4. Ask each question via typer prompt (or use `--answer key=value` flags for non-interactive)
5. Render all files in the template through Jinja2, substituting questionnaire answers
6. Write the rendered workspace to the target directory
7. Run `validate_workspace()` on the result

**Key function signature:**
```python
def build_workspace(
    template_name: str,
    target_dir: Path,
    answers: dict[str, str] | None = None,
) -> Path:
    ...
```

**Verification:**
- Test that `build_workspace("script-to-animation", tmpdir, {"topic": "AI safety"})` creates a valid workspace.
- Test that questionnaire answers are substituted into rendered files.

**Commit:** `git add src/icmpy/builder.py tests/test_builder.py && git commit -m "feat: workspace builder with jinja2 templates"`

---

### Task 11: Create the "script-to-animation" built-in template

**Objective:** Port the paper's example workspace into a built-in template.

**Files:**
- Create: `src/icmpy/templates/script_to_animation/stages/01_research/CONTEXT.md`
- Create: `src/icmpy/templates/script_to_animation/stages/01_research/references/structure.md`
- Create: `src/icmpy/templates/script_to_animation/stages/02_script/CONTEXT.md`
- Create: `src/icmpy/templates/script_to_animation/stages/03_production/CONTEXT.md`
- Create: `src/icmpy/templates/script_to_animation/_config/voice.md`
- Create: `src/icmpy/templates/script_to_animation/questionnaire.json`

**questionnaire.json:**
```json
[
  {
    "key": "topic",
    "question": "What is the topic for this video?",
    "type": "text"
  },
  {
    "key": "target_duration",
    "question": "Target video duration in seconds?",
    "type": "integer",
    "default": 90
  }
]
```

Each stage CONTEXT.md should include Inputs, Process, and Outputs sections as described in the paper (Section 3.3). Use Jinja2 placeholders like `{{ topic }}` where user input is needed.

**Verification:** Build from this template and validate the output.

**Commit:** `git add src/icmpy/templates/script_to_animation/ && git commit -m "feat: script-to-animation built-in template"`

---

## Phase 5: Stage Execution

### Task 12: Implement `icmp stage list`

**Objective:** Show all stages in the current workspace with their order and status.

**Files:**
- Modify: `src/icmpy/cli.py`
- Create: `src/icmpy/stages.py`

**Behavior:**
- Scan `stages/` for numbered folders
- Parse each stage's `CONTEXT.md` for the contract
- Display: number, name, input files, output files
- Status: check if `output/` contains files → mark as "completed", else "pending"

Use `rich.table.Table` for formatted output.

**Verification:** `icmp stage list` in a workspace with 2 stages shows both with correct status.

**Commit:** `git add src/icmpy/stages.py tests/test_stages.py && git commit -m "feat: stage list command"`

---

### Task 13: Implement `icmp stage run <stage>`

**Objective:** Execute a single stage by building its context bundle and handing off to an AI agent (or simulating it).

**Files:**
- Modify: `src/icmpy/stages.py`
- Modify: `src/icmpy/cli.py`

**Behavior:**
1. Validate the workspace
2. Find the stage by number or name
3. Gather context according to the stage contract:
   - Layer 0: `CLAUDE.md`
   - Layer 1: `CONTEXT.md`
   - Layer 2: stage's `CONTEXT.md`
   - Layer 3: files listed in Inputs with `layer: 3`
   - Layer 4: files listed in Inputs with `layer: 4`
4. Assemble into a single context bundle (or save to a temp file)
5. Print the assembled context to stdout (for now — in v2 this will call an LLM API)
6. Create a `output/` directory for the stage if it doesn't exist
7. Write a placeholder output file indicating the stage was "run"

This is intentionally lightweight. The paper states the orchestrating agent reads the files; `icmp stage run` is a helper that assembles the context for the user to paste into their AI tool.

**Context bundle format:**
```
=== Layer 0: Workspace Identity ===
[contents of CLAUDE.md]

=== Layer 1: Workspace Routing ===
[contents of CONTEXT.md]

=== Layer 2: Stage Contract (01_research) ===
[contents of stages/01_research/CONTEXT.md]

=== Layer 3: Reference Material ===
[file: _config/voice.md]
[contents]

=== Layer 4: Working Artifacts ===
[file: stages/01_research/output/source_material.md]
[contents]
```

**Verification:**
- Test that running a stage produces the expected context bundle.
- Test that output directory is created and contains a placeholder.

**Commit:** `git add src/icmpy/stages.py tests/test_stage_run.py && git commit -m "feat: stage run command assembles context bundle"`

---

## Phase 6: Polish & Documentation

### Task 14: Write a comprehensive README.md

**Objective:** Document installation, quickstart, commands, and the ICM methodology for users.

**Files:**
- Modify: `README.md`

**Sections:**
- What is ICM? (1 paragraph + link to paper)
- Installation: `pip install icmpy` (or `uv pip install icmpy`)
- Quickstart: `icmp init my-workspace`, `cd my-workspace`, edit `CONTEXT.md`, `icmp stage run 01`
- Commands reference table
- Workspace structure explanation with the five layers
- Workspace builder: `icmp build`
- Contributing / Development setup

**Verification:** Render with `cat README.md` and verify completeness.

**Commit:** `git add README.md && git commit -m "docs: comprehensive README with quickstart"`

---

### Task 15: Add `--dry-run` and `--verbose` flags globally

**Objective:** Improve CLI UX with common global options.

**Files:**
- Modify: `src/icmpy/cli.py`

**Behavior:**
- `--dry-run` on `init`, `build`, `stage run`: show what would happen without writing files
- `--verbose` / `-v`: print debug info (file paths loaded, token count estimates, etc.)
- Store these in a typer context object so subcommands can access them

**Verification:** `icmp init --dry-run test` prints actions but creates no directory.

**Commit:** `git add src/icmpy/cli.py tests/test_cli_flags.py && git commit -m "feat: add --dry-run and --verbose flags"`

---

### Task 16: Token count estimation for context bundles

**Objective:** Help users stay within optimal context window sizes (per paper, 2k–8k tokens per stage).

**Files:**
- Create: `src/icmpy/tokens.py`

**Behavior:**
- Simple tokenizer: split on whitespace, multiply by ~1.3 to approximate GPT/claude tokenization
- In `stage run`, print "Estimated context tokens: N" in verbose mode
- Warn if estimated tokens > 8,000

**Verification:** `python -c "from icmpy.tokens import estimate; assert estimate('hello world') > 0"`

**Commit:** `git add src/icmpy/tokens.py tests/test_tokens.py && git commit -m "feat: context token estimation"`

---

## Phase 7: Final Validation

### Task 17: Run full test suite and linting

**Objective:** Ensure everything passes.

**Commands:**
```bash
ruff check src/ tests/
ruff format --check src/ tests/
mypy src/
pytest -v --cov=icmpy --cov-report=term-missing
```

**Commit:** Fix any issues, then commit with `git commit -m "chore: final linting and test fixes"`

---

## Open Questions / Future Work (not in this plan)

1. **LLM integration:** Should `icmp stage run` actually call an LLM API (OpenAI, Anthropic)? If so, add an `--agent` flag and MCP support. The current plan keeps it as a context assembler to stay true to the paper's human-in-the-loop design.
2. **Custom templates:** Allow users to register their own templates from git repos or local paths.
3. **Incremental execution:** Track file hashes to know which stages need re-running when inputs change (Section 6.1 of the paper).
4. **Cross-stage trace verification:** Implement the "Verify" section of stage contracts for semantic debugging (Section 6.2).
5. **Edit-to-source feedback:** Track human edits to stage outputs and suggest source-level improvements (Section 6.3).
