# Gurobi Revise-code results for KDD Table 2

This directory tracks the Gurobi **Revise (code)** column in Table 2 of the
OR-Space KDD manuscript. It is intentionally split into a paper snapshot and
an evidence review:

- `table2_snapshot.csv` is an exact transcription of the manuscript column.
- `provenance_review.csv` records which historical or recovered result cell
  can support each paper value.
- `release_manifest.json` pins the manuscript commit and records release
  blockers.

The table snapshot is **not** itself experimental evidence. A cell is
reproducible only when the corresponding row in `provenance_review.csv` is
marked `ready` and the public bundle contains 100 unique per-instance rows,
raw/extracted outputs, execution logs, prompt and environment hashes, and an
immutable run manifest.

## Current status

The current snapshot contains 18 model rows. Several values match recovered
first-call results, but the bundle is not yet ready for an archival release:

- `gemini-3.1-pro` at 87 is from a historical canonical cell containing five
  post-hoc temperature-0.7 substitutions; the recovered first-call score is
  92.
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
