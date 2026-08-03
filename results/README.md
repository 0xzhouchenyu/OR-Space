# Paper result snapshots

`table2_main_results.csv` is an exact machine-readable transcription of the
current 18-model main table. `gurobi/revise_code.csv` extracts the default
Revise-code/Gurobi column and is checked against the main snapshot in CI-style
release validation.

These files are aggregate paper snapshots. Their column names reproduce the
manuscript, but the released Revise-code column contains documented row-level
protocol exceptions: three models use conservative repeated-run rules and one
uses infrastructure recovery. See
[`../baseline_outputs/gurobi/revise_code_protocol.csv`](../baseline_outputs/gurobi/revise_code_protocol.csv)
before treating individual rows as standard Pass@1. New evaluations should
publish per-instance outputs and a run manifest rather than editing these rows.

`protocol.json` records the manuscript's default Filesystem, Revise-code,
Gurobi 13.0.1, 180 s, objective-scoring, and Explain-judge settings, together
with a pointer to the row-level Revise provenance audit.
