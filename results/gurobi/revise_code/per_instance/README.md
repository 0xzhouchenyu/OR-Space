# Per-instance Gurobi Revise-code records

`instance_catalog.csv` identifies the 100 Revise-code benchmark workspaces and
pins each workspace with a SHA-256 tree hash. `results.csv` is the complete
18-model by 100-instance matrix for the manuscript snapshot.

The current matrix is an explicit availability inventory. Blank attempt fields
mean that the raw per-instance run is not present in this public checkout; they
are not failed answers and are not used to reconstruct a paper score.

## Metric semantics

- `pass_at_1` is the outcome of the first attempt.
- `pass_both_at_2` is
  `attempt_1_passed AND attempt_2_passed` for each instance. It is reported as
  **PassBoth@2**, a repeatability/consistency metric in which both runs must
  pass.
- Attempt 2 may cover all instances or only first-attempt passes. The latter is
  sufficient for PassBoth@2 because a first-attempt failure can never pass the
  two-run intersection.
- `conditional_resample_*` retains any other diagnostic reruns separately.

PassBoth@2 is not the conventional Pass@2 metric, which normally means that at
least one of two samples succeeds. PassBoth@2 can be lower than Pass@1. For
example, if Gemini-3.1-Pro passes 92 first attempts and five of those fail the
second run, its PassBoth@2 result is 87/100.

## Materialization

Create the placeholder inventory from the staged code-visible workspaces:

```bash
python tools/materialize_revise_per_instance.py \
  --benchmark-root local_release/kdd-code/revise_workspaces \
  --snapshot results/gurobi/revise_code/table2_snapshot.csv \
  --catalog-out results/gurobi/revise_code/per_instance/instance_catalog.csv \
  --results-out results/gurobi/revise_code/per_instance/results.csv
```

Once immutable first- and second-attempt trees are available, add:

```bash
  --attempt-1-root /immutable/revise-code-attempt-1 \
  --attempt-2-root /immutable/revise-code-attempt-2 \
  --attempt-2-policy first_passes_only
```

Each root must contain
`<artifact_model>/results.json` and may contain per-instance `raw/`, `code/`,
`stdout/`, `stderr/`, and `prompts/` directories. The generated table records
canonical result-row hashes and artifact-bundle hashes without exposing local
absolute paths.
