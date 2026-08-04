# Representative Gurobi traces

This directory contains complete trace archives for two representative models:
`gpt-5.4` and `deepseek-v4-flash`. Each archive contains 100 Build, 100
Revise-code, and 100 Explain records with the following layout:

```text
<model>/
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

Some artifact directories may be absent when a response did not produce that
artifact type. Each task-level `results.json` still contains one row for every
instance. The archives include generated programs, raw responses, execution
logs, Explain answers, stored criterion-level scores, and task summaries.
Participant-visible workspace inputs are stored once under
`workspace_benchmark/` and can be joined through each archive's
`provenance.json`.

`model_index.csv` lists archive paths, sizes, checksums, and completeness
counts. Validate an archive from this directory with:

```bash
sha256sum -c <(awk -F, 'NR>1 {print $4 "  " $2}' model_index.csv)
unzip -t models/gpt-5.4.zip
```

On macOS, use `shasum -a 256` to check individual files.
