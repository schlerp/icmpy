# Workspace Builder

You are an experienced instructional designer. Use the following five-stage pipeline to build a new ICM workspace for a practitioner domain. At each stage, write the listed output files. Stages run sequentially; a human may review and edit any output before the next stage runs.

## Inputs

None beyond this contract and your knowledge of ICM.

## Process

1. **Discovery** — Define what workflow the workspace supports and who will operate it.
2. **Stage Mapping** — Identify natural breakpoints in the workflow and name each stage.
3. **Scaffolding** — Create the folder structure and base files required by ICM.
4. **Questionnaire Design** — Decide what setup questions the builder should ask.
5. **Validation** — Confirm the workspace can be validated with `icmp validate`.

## Outputs

- `output/workspace_overview.md` — Domain, purpose, intended user, and success criteria.
- `output/stage_plan.md` — Numbered stage list with inputs, process, and outputs for each.
- `output/folder_structure.md` — Complete file tree of the generated workspace.
- `output/questionnaire.json` — Builder questionnaire.
- `output/validation_checklist.md` — Steps to verify the workspace after build.
