# Build and Revise scoring

Build and Revise are scored by executing a complete solver-specific Python
program and parsing its final solver status and objective. An instance passes
only when the program executes, reports `Optimal`, and its objective is within
1% relative error of the reference:

```text
abs(objective - reference) / max(1, abs(reference)) <= 0.01
```

Use the references published in the dataset repository:
`oracle/build_revise_objectives.csv`.

The prediction file is JSONL with one row per attempted instance:

```json
{"workspace_id":"or_space_001_build","status":"Optimal","objective":219816.0}
```

Score it with:

```bash
python evaluation/build_revise/score_objectives.py \
  --references oracle/build_revise_objectives.csv \
  --predictions predictions.jsonl \
  --output scored.jsonl \
  --summary summary.json \
  --task build
```

Use `--task revise` for the Revise split, or omit `--task` when the prediction
file contains both tasks. Missing instances count as failures unless
`--allow-missing` is supplied.
Runtime failures should still be recorded with their final status and a null
objective so that the denominator remains the full 100-instance task split.
