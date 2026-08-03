# Gurobi baselines

This directory contains the complete Gurobi trace release for the 18 models in
the OR-Space main table: 100 Build, 100 Revise-code, and 100 Explain records per
model (5,400 model-by-instance records in total). Each archive has the following
layout:

```text
<paper-model>/
  provenance.json
  build/
    results.json
    summary.json
    raw/
    code/
    stdout/
    stderr/
  revise_code/
    results.json
    summary.json
    raw/
    code/
    stdout/
    stderr/
    prompts/
  explain/
    results.json
    summary.json
    raw/
    answers/
    scores/
```

Some directories are absent for instances where the model or provider returned
no usable artifact. `results.json` still contains exactly one record for every
instance from 1 through 100.

The files are the model-level traces, not only aggregate table exports. They
include raw model responses; generated solver programs and their stdout/stderr
for code-producing tasks; Revise prompts where recorded; Explain answers and
criterion-level stored scores; and task summaries. Common participant-visible
workspace inputs are published once in the dataset and can be joined by the
rules in each archive's `provenance.json`.

`provenance.json` states the artifact-model name, task-to-workspace join rule,
paper metrics, stored checks, and Revise-code release mode.

## Revise-code protocol provenance

The archives reproduce the paper-aligned Revise-code column, but not every row
is an ordinary first-call Pass@1 result. The exact row-level classification is
released in [`revise_code_protocol.csv`](revise_code_protocol.csv):

- `gemini-3.1-pro`, `claude-opus-4-6`, and `claude-sonnet-4.5` use conservative
  repeatability rules involving a second run; their published values are not
  standard Pass@1.
- `gemini-3-flash` includes recovery of calls affected by infrastructure
  failures and is marked as a recovery composite.
- the remaining 14 rows restore the historical first call and are marked
  `pass_at_1`.

The affected archives retain source-run artifacts where available. This
separation preserves the manuscript numbers while making their evidence and
measurement provenance explicit.

Validate an archive with:

```bash
sha256sum -c <(awk -F, 'NR>1 {print $5 "  " $3}' model_index.csv)
unzip -t models/gemini-3.1-pro.zip
```

The checksum command should be run from `baseline_outputs/gurobi/`. On macOS,
use `shasum -a 256` to check individual files.
