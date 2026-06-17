# Production

Convert the approved script into animation specifications and working Remotion code.

## Inputs

- Layer 4 (working): `../02_script/output/script_draft.md` — the approved script.
- Layer 3 (reference): `../../_config/voice.md` — voice and tone guide.
- Layer 3 (reference): `../../_config/structure.md` — structural template.

## Process

1. Read the script and reference material.
2. Produce animation specifications keyed to script sections.
3. Generate working Remotion source files in the output folder.
4. Verify timing: every visual beat must align with a script phrase.

## Outputs

- `output/animation_spec.md` — visual and timing specification.
- `output/Video.tsx` — working Remotion component.

## Verify

- Each scene's timing matches the corresponding script section.
- Total runtime stays within {{ target_duration }} seconds.
