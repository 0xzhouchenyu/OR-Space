# Paper result snapshots

`table2_main_results.csv` is an exact machine-readable transcription of the
current 18-model main table. `gurobi/revise_code.csv` extracts the default
Revise-code/Gurobi column and is checked against the main snapshot in CI-style
release validation.

These files are aggregate paper snapshots. They should not be substituted with
older server reruns or with a different revision-context or repeatability
metric. New evaluations should publish their own per-instance outputs and run
manifest rather than editing these rows.

`protocol.json` records the manuscript's default filesystem, Revise-code,
Gurobi 13.0.1, 180 s, objective-scoring, and Explain-judge settings.
