# OR-Space evaluation

This directory contains the public scoring protocol used by the released
OR-Space task views.

- [`build_revise/`](build_revise/) scores solver-specific Build and Revise
  programs from their reported status and objective value.
- [`explain/`](explain/) prepares evidence-grounded judge inputs and combines
  deterministic checklist checks with the five-dimensional Explain rubric.

The evaluator is separate from model execution. Build and Revise submissions
must be complete programs for the selected solver API (`gurobipy`, `coptpy`,
PuLP/CBC, or `highspy`). The public scorer does not translate one solver API
to another and does not mount a backend behind a common PuLP model.

For paper comparisons, pin this repository commit. Also report the model
endpoint, prompt, solver version, timeout, and, for Explain, the independent
judge model.

Validate a downloaded snapshot with:

```bash
python evaluation_programs/validate_dataset.py
```
