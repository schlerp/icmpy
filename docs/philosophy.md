# ICM Philosophy

This document summarizes the design principles behind the Interpretable Context Methodology and how `icmpy` implements them.

## Folder structure as architecture

In ICM, the filesystem does the work that multi-agent frameworks usually do in code:

- **Sequencing** is folder numbering.
- **Context scoping** is folder boundaries.
- **State management** is files on disk.
- **Handoffs** are one stage's `output/` becoming another stage's input.

## Five layers of context

| Layer | File | Purpose |
|---|---|---|
| 0 | `CLAUDE.md` | Workspace identity — "Where am I?" |
| 1 | `CONTEXT.md` | Routing — "Where do I go?" |
| 2 | `stages/NN/CONTEXT.md` | Stage contract — "What do I do?" |
| 3 | `_config/` and `references/` | Stable reference material |
| 4 | `output/` | Per-run working artifacts |

`icmp stage run` assembles only the layers a stage actually needs, keeping the context window focused.

## Human-in-the-loop

Every intermediate output is a plain markdown file. Humans can:

- Read it
- Edit it
- Save it
- Commit it to version control

The next stage always reads whatever is on disk, so human corrections are first-class citizens of the pipeline.

## Unix virtues

ICM borrows from Unix pipelines, Make, and multi-pass compilers:

- One stage, one job
- Plain text as the universal interface
- Human-readable intermediate representations
- Incremental recompilation (re-run only the stages that changed)

## When ICM fits

ICM is best for workflows that are:

- **Sequential** — step 2 follows step 1
- **Reviewable** — a human should check each output
- **Repeatable** — the same pipeline runs many times with different input

It is not a replacement for real-time multi-agent collaboration, high-concurrency systems, or complex automated branching.
