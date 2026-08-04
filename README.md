<p align="center">
  <img src="figs/logo.png" width="96" alt="OR-Space logo">
</p>

# OR-Space

**A full-lifecycle workspace benchmark for industrial optimization agents.**

[![License](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)
[![Benchmark](https://img.shields.io/badge/Tasks-300%20workspace%20views-005BBB)](#benchmark)

OR-Space evaluates whether language-model agents can perform reliable operations
research work inside executable, multi-file workspaces. Each instance separates
business requirements, structured parameter files, code artifacts, solver state,
and evaluation targets instead of flattening the optimization problem into one
prompt.

<p align="center">
  <img src="figs/main.png" width="860" alt="Overview of the OR-Space Build, Revise, and Explain benchmark">
</p>

## Anonymous Review Artifact

This repository is the anonymized code, data, and evaluation artifact for the
double-anonymous submission. Public project, author, and citation metadata will
be added after the review period.

## Benchmark

OR-Space contains 100 industrial optimization topologies, each rendered as three
task views on the same underlying mathematical problem:

| Task | What the agent receives | What is evaluated |
| --- | --- | --- |
| Build | Business documents, tabular data, and an empty `src/` scaffold | Whether the agent can write solver-ready code from heterogeneous files |
| Revise | Original workspace, revised requirements, updated data, and legacy heuristic code | Whether the agent can preserve valid logic while implementing changed requirements |
| Explain | Original and revised workspaces plus recorded solver artifacts | Whether the agent can ground an explanation in code, data, solver state, and OR theory |

Build and Revise are scored by executing the submitted solver program and
matching the reference objective value within 1% relative error. Explain is
scored with exact-match checklist items plus rubric-based judgments for
reasoning, grounding, answer quality, and hallucination control.

The default paper track uses the filesystem interface, Revise-code context,
and Gurobi. Build and Revise submissions are complete solver-specific programs;
each backend track uses its corresponding API rather than a shared PuLP model
with a backend mounted by the evaluator.

## Quick Start

Install the lightweight validation dependency:

```bash
pip install -U pandas
```

Inspect the bundled task index directly:

```bash
python - <<'PY'
import pandas as pd

index = pd.read_csv("supporting_files/metadata/workspace_index.csv")
print(index.groupby(["task_type", "difficulty"]).size())
print(index.head()[["workspace_id", "task_type", "workspace_path"]])
PY
```

The workspaces follow this pattern:

```text
workspace_benchmark/
  build/instance_1/
    docs/
    data/
    src/
    metadata.json
  revise/instance_1/
    original/
    revised/
    metadata.json
  explain/instance_1/
    original/
    revised/
    solver_artifacts/
    metadata.json
```

## What This Repo Contains

This repository contains the participant dataset, generation utilities,
runnable evaluators, and machine-readable result snapshots used by the paper.

```text
.
  README.md
  LICENSE
  workspace_benchmark/      100 Build, 100 Revise, and 100 Explain workspaces
  evaluation/               Evaluator-only references for all three tasks
  evaluation_programs/      Public executable scoring programs
  supporting_files/         Index, difficulty labels, split, and documentation
  figs/                     Project-page figures
  01_build/                 Build workspace generation utilities
  02_revise_modeling/       Revise workspace generation utilities
  03_revise_business/       Business-voice rewriting utilities
  04_difficulty_judge/      Difficulty judging utilities
  05_business_quality_rubric/
  06_static_diff/           Static revision-diff analysis
  results/                  Machine-readable paper table snapshots
  tools/                    Participant staging and release validation
  tests/                    Evaluator smoke tests
```

The artifact contains all 300 participant-visible task views, Build and Revise
objective references, all 100 Explain rubrics and checklists, empirical
difficulty labels, and the public-test split. Participant workspaces and
evaluator-only labels are kept in separate top-level paths so models are not
accidentally given reference code or answers.

## Empirical Difficulty

Difficulty labels are derived separately for each task from observed benchmark
performance under a fixed evaluation panel. Build and Revise use executable
pass rates, while Explain uses the mean rubric score. Boundaries approximate
tertiles without splitting tied scores. The resulting Easy/Medium/Hard counts
are 35/32/33 for Build, 39/30/31 for Revise, and 33/33/34 for Explain. See
[`supporting_files/metadata/difficulty_methodology.md`](supporting_files/metadata/difficulty_methodology.md)
and [`supporting_files/metadata/empirical_difficulty.csv`](supporting_files/metadata/empirical_difficulty.csv).

## Evaluation

See [`evaluation_programs/`](evaluation_programs/) for runnable scorers and
[`evaluation/`](evaluation/) for evaluator-only references. The Explain release
includes deterministic normalized entity checks, criterion-level semantic
judgments, verified workspace evidence, the independent judge prompt and JSON
schema, and aggregation into the paper's 35/35/20/10 rubric with an unsupported-
claim penalty of up to 12 points.

Validate the complete anonymous snapshot with:

```bash
python evaluation_programs/validate_dataset.py
```

The current 18-model Table 2 snapshot is published in
[`results/table2_main_results.csv`](results/table2_main_results.csv). Its
Revise-code/Gurobi column is also available separately in
[`results/gurobi/revise_code.csv`](results/gurobi/revise_code.csv); release
validation checks that the two remain identical.

The frozen aggregate results needed to reproduce the paper tables are included
under [`results/`](results/). Raw per-instance execution archives are
intentionally omitted from the anonymous review snapshot because execution
logs may contain identifying machine paths. The packaging script is
[`tools/package_gurobi_baselines.py`](tools/package_gurobi_baselines.py); it
requires all 18 Build and Revise-code aggregates to match Table 2 before it
writes any archive for the post-review release.

## Main Paper Findings

| Finding | Result |
| --- | --- |
| Workspace construction remains hard | The best Build score is 72.0% Pass@1 |
| Revision context is model-dependent | Legacy heuristic code helps strong models but hurts weaker models |
| Explanation is a distinct capability | Explain scores are weakly correlated with Build and Revise success |

These results should be interpreted as benchmark evidence about synthetic,
executable OR workspaces, not as a deployment certificate for production
optimization systems.

## Review Snapshot

The anonymous artifact is pinned to a fixed submission snapshot. Public release
URLs, archival tags, and citation metadata will be added after the review
period.

## License

The dataset release is for non-commercial research use under CC BY-NC
4.0-compatible terms, following the inherited license constraints of the
IndustryOR seed topologies. Proprietary solver binaries, commercial API
credentials, and third-party model services are not redistributed.
