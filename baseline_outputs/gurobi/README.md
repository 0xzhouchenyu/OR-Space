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
paper metrics, stored checks, and the Revise-code release mode. For conservative
two-run Revise results, the archive also retains the source-run artifacts needed
to reproduce the per-instance rule.

Validate an archive with:

```bash
sha256sum -c <(awk -F, 'NR>1 {print $5 "  " $3}' model_index.csv)
unzip -t models/gemini-3.1-pro.zip
```

The checksum command should be run from `baseline_outputs/gurobi/`. On macOS,
use `shasum -a 256` to check individual files.
