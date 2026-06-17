# Script

Turn the research output into a voice-matched script.

## Inputs

- Layer 4 (working): `../01_research/output/research_output.md` — research summary.
- Layer 3 (reference): `../../_config/voice.md` — voice and tone guide.
- Layer 3 (reference): `../../_config/structure.md` — structural template.

## Process

1. Read the research output.
2. Follow the structural template.
3. Match the tone described in the voice guide.
4. Keep the script under {{ target_duration }} seconds when read aloud.

## Outputs

- `output/script_draft.md` — the finished script.
