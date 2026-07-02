# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

## [0.0.4] - 2026-07-02

### Added

- LLM harness dispatch: `icmp stage run <stage> --harness <name>` sends the assembled context bundle directly to Claude Code, OpenAI Codex, OpenCode, or `pi`, saving the harness response to the stage's `output/` directory.
- New `icmp harness list` command to show available harness adapters.
- `--dry-run` support for harness dispatches so you can preview the exact command before executing it.

## [0.0.3] - 2026-07-02

### Added

- New `icmp reset` command to clear run flags for a single stage or the whole workspace, with optional `--remove-outputs` to delete stage `output/` directories.

## [0.0.2] - 2026-06-21

### Added

- Custom template support: copy built-in templates, list templates, and validate templates with the `icmp template` family of commands.
- Expanded custom template documentation and walkthrough examples.

## [0.0.1] - 2026-06-17

### Added

- Initial CLI: `init`, `validate`, `build`, `stage list`, `stage run`
- Workspace validation engine for ICM five-layer structure
- 13 built-in templates across content, education, research, software, marketing, and operations
- Interactive template builder with support for text, integer, and confirm question types
- `icmp stage run next` to auto-select the first pending stage
- `icmp status` command for workspace health and progress summary
- `icmp build --answers-file` for non-interactive builds
- `icmp completion` for bash, zsh, and fish
- Token-count estimation with 8k-context warning
- Markdown-formatted context bundles
- Documentation: README, docs, custom templates guide, CONTRIBUTING, and CLI tips
