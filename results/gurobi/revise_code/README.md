# Gurobi Revise-code results for KDD Table 2

This directory tracks the Gurobi **Revise (code)** column in Table 2 of the
OR-Space KDD manuscript. It is intentionally split into a paper snapshot and
an evidence review:

- `table2_snapshot.csv` is an exact transcription of the manuscript column.
- `provenance_review.csv` records which historical or recovered result cell
  can support each paper value.
- `release_manifest.json` pins the manuscript commit and records release
  blockers.
- `per_instance/` contains the 100-question catalog and the complete
  model-by-instance availability matrix.
- `pass_both_at_2_available.csv` records the nine current-table models for
  which the historical repeatability experiment resampled every first-attempt
  pass.

The table snapshot is **not** itself experimental evidence. A cell is
reproducible only when the corresponding row in `provenance_review.csv` is
marked `ready` and the public bundle contains 100 unique per-instance rows,
raw/extracted outputs, execution logs, prompt and environment hashes, and an
immutable run manifest.

The per-instance schema distinguishes two metrics:

- **Pass@1**: the first-attempt outcome used by the current manuscript header.
- **PassBoth@2**: a repeatability metric that passes an instance only when both
  attempts pass. It is an intersection, not conventional Pass@2.

For Gemini-3.1-Pro, 92 first attempts passed and five of those failed the
higher-temperature repeat, yielding 87 instances that passed both. That 87 can
be reported as PassBoth@2 once its complete per-instance first/second artifacts
are materialized. It must not be mixed into a column whose other rows are
Pass@1.

Only Gemini-3.1-Pro and Claude Sonnet 4.5 currently have Table 2 values equal
to their available PassBoth@2 aggregates. The other seven repeatability cells
do not match the manuscript snapshot, and the remaining manuscript models lack
a comparable second-attempt set. This is why the current Table 2 column cannot
be relabeled wholesale.

## Current status

The current snapshot contains 18 model rows. Several values match recovered
first-call results, but the bundle is not yet ready for an archival release:

- `gemini-3.1-pro` at 87 is the intersection of 92 first-attempt passes and
  their temperature-0.7 repeats, five of which failed. This supports a
  PassBoth@2 interpretation, not the current Pass@1 header.
- No matching 87/100 Gurobi Revise-code cell has been located for
  `claude-opus-4-6`; the available historical cell is 90/100.
- `claude-sonnet-4.5` at 82 is a historical cell affected by substitutions
  and infrastructure rows; the recovered first-call score is 89.
- `qwen3.5-27b` at 48 still includes unresolved zero-token/infrastructure
  rows.
- The local public checkout does not currently contain the complete
  per-instance artifacts for the remaining cells.

These rows must be resolved by changing the paper to a clean, uniformly
defined result inventory or by running a clean evaluation under the published
protocol. They must not be made to match by deleting, relabeling, or replacing
per-instance outcomes.

## Validation

Run the structural check:

```bash
python tools/validate_table2_revise_release.py \
  results/gurobi/revise_code \
  --allow-provisional
```

Omit `--allow-provisional` for the archival gate. That command intentionally
fails while any row lacks complete public evidence or has an unresolved
protocol issue.
