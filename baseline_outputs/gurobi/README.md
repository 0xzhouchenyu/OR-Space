# Gurobi baselines

This directory contains representative Gurobi traces for two models from the
OR-Space main table: `gpt-5.4` and `deepseek-v4-flash`.
Each archive contains 100 Build, 100 Revise-code, and 100 Explain records, for
600 model-by-instance records in total, with the following layout:

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

## Revise-code result provenance

Both public trace archives restore the historical first-call Revise-code run.
The 18-model aggregate paper snapshot remains in `results/`; its row-level
classification is documented in
[`revise_code_protocol.csv`](revise_code_protocol.csv):

- `gemini-3.1-pro`, `claude-opus-4-6`, and `claude-sonnet-4.5` use conservative
  repeatability rules involving a second run; their published values are not
  standard Pass@1.
- `gemini-3-flash` includes recovery of calls affected by infrastructure
  failures and is marked as a recovery composite.
- the remaining 14 rows restore the historical first call and are marked
  `pass_at_1`.

The protocol table is aggregate-result metadata, not an additional model-trace
release.

Validate an archive with:

```bash
sha256sum -c <(awk -F, 'NR>1 {print $5 "  " $3}' model_index.csv)
unzip -t models/gpt-5.4.zip
```

The checksum command should be run from `baseline_outputs/gurobi/`. On macOS,
use `shasum -a 256` to check individual files.
