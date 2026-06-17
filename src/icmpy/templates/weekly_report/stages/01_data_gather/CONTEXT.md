# Data Gather

Collect the raw metrics for the reporting period.

## Inputs

- Layer 3 (reference): `_config/voice.md`

## Process

1. Pull key numbers from {{ data_source }} for {{ reporting_period }}.
2. Record them without interpretation.

## Outputs

- `output/raw_metrics.md` — table of metrics.
