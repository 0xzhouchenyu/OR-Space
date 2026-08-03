# Anonymous Review Dataset

This directory contains the frozen data snapshot used by the anonymous
submission. It includes the participant-visible workspaces and the
evaluator-only labels needed to reproduce the reported metrics.

## Contents

- `build-revise-explain_workspaces.zip`: 300 participant-visible workspace
  views covering Build, Revise, and Explain.
- `metadata/workspace_index.csv`: one row per workspace view.
- `metadata/schema.md`: field and layout documentation.
- `splits/public_test.json`: the evaluation split definition.
- `oracle/build_revise_objectives.csv`: reference objectives for the 200
  executable Build and Revise tasks.
- `explain_rubrics/`: the 100 Explain checklists, normalization rules, judge
  prompt, and machine-readable schema.
- `MANIFEST.json`: byte sizes and SHA-256 checksums for the frozen files.

The workspace archive contains participant inputs only. Keep `oracle/` and
`explain_rubrics/` outside the model-visible workspace when running an
evaluation.

## Unpack

From the repository root:

```bash
unzip data/build-revise-explain_workspaces.zip -d data/
```

This creates `data/build-revise-explain_workspaces/`.

Raw model-execution archives are not included in this review snapshot because
their logs contain machine-local paths. The anonymized aggregate result
snapshots used by the paper are available in `../results/`.
