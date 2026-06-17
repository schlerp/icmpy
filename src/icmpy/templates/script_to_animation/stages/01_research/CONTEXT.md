# Research

Transform the topic brief into a structured research document that the script stage can use.

## Inputs

- Layer 4 (working): `output/topic_brief.md` — the topic brief for this run. Create it before running this stage if it does not exist.
- Layer 3 (reference): `_config/voice.md` — high-level voice conventions.

## Process

1. Read the topic brief. Topic: {{ topic }}.
2. Identify key points, narrative angles, and supporting data.
3. Structure findings into a concise research document.

## Outputs

- `output/research_output.md` — structured research summary.
