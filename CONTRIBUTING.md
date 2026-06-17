# Contributing to icmpy

Thanks for your interest in contributing.

## Development setup

```bash
git clone https://github.com/eduba/icmpy.git
cd icmpy
uv sync --extra dev
source .venv/bin/activate
```

## Running checks

Before committing, run the full check suite:

```bash
ruff check src/ tests/
ruff format --check src/ tests/
mypy src/
pytest
```

## Adding a template

1. Create a new folder under `src/icmpy/templates/`.
2. Add `questionnaire.json`, `_config/voice.md`, and stage `CONTEXT.md` files.
3. Register the template in `src/icmpy/templates/builtins_manifest.json`.
4. Add a test in `tests/` that builds the template and checks key substitutions.
5. Update the README template table.

## Commit style

Use conventional commits:

- `feat:` for new features or templates
- `fix:` for bug fixes
- `docs:` for documentation changes
- `style:` for formatting/linting
- `test:` for test-only changes

## Questions?

Open an issue or start a discussion in the repo.
