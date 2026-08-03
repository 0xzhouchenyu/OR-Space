<p align="center">
  <img src="figs/logo.png" width="96" alt="OR-Space logo">
</p>

# OR-Space

**A full-lifecycle workspace benchmark for industrial optimization agents.**

[![Dataset](https://img.shields.io/badge/Hugging%20Face-Dataset-ffcc4d)](https://huggingface.co/datasets/Chenyu-Zhou/OR-Space)
[![License](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)
[![Benchmark](https://img.shields.io/badge/Tasks-300%20workspace%20views-005BBB)](#benchmark)

OR-Space evaluates whether language-model agents can perform reliable
operations research work in executable, multi-file workspaces. Each instance
separates business requirements, structured data, code artifacts, solver state,
and evaluation targets instead of flattening the problem into one prompt.

<p align="center">
  <img src="figs/main.png" width="860" alt="Overview of the OR-Space Build, Revise, and Explain benchmark">
</p>

## Benchmark

OR-Space contains 100 industrial optimization topologies, each represented by
three task views of the same underlying problem.

| Task | Participant-visible artifacts | Evaluation |
| --- | --- | --- |
| Build | Business documents, tabular data, and an empty `src/` directory | Execute generated code and compare its objective with the oracle |
| Revise | Revised documents and data plus the correct Build implementation | Execute the revised program and compare its objective with the revised oracle |
| Explain | Correct original and revised workspaces, execution logs, and solver records | Score checklist coverage, reasoning, evidence grounding, answer quality, and unsupported claims |

Build and Revise require an `Optimal` status and an objective within 1% relative
error of the reference value. Explain uses instance-specific checklists and the
released rubric. The paper's default track uses the Filesystem interface,
Revise-code context, and Gurobi. Solver tracks require complete programs written
against the corresponding solver API.

## Repository contents

This repository is the complete research release. Participant workspaces and
evaluation references are available from the
[OR-Space dataset](https://huggingface.co/datasets/Chenyu-Zhou/OR-Space); this
repository additionally contains benchmark construction code, paper snapshots,
and model-run evidence.

```text
.
├── 01_build/ ... 06_static_diff/  Benchmark construction and analysis code
├── evaluation/                    Build, Revise, and Explain evaluators
├── benchmark_metadata/            Workspace index and empirical difficulty labels
├── results/                       Machine-readable paper-result snapshots
├── baseline_outputs/gurobi/       Full Gurobi traces for 18 models and three tasks
├── tools/                         Packaging and release-validation utilities
└── tests/                         Evaluator tests
```

The 18 model archives contain 5,400 model-by-instance records: 100 Build, 100
Revise-code, and 100 Explain records for each model. Generated programs, raw
responses, execution logs, answers, stored scores, checksums, and provenance are
retained where available. See
[`baseline_outputs/gurobi/`](baseline_outputs/gurobi/) for archive structure and
the row-level Revise protocol audit.

## Dataset quick start

```bash
pip install -U huggingface_hub pandas
huggingface-cli download Chenyu-Zhou/OR-Space \
  --repo-type dataset --local-dir OR-Space
```

```python
import pandas as pd

index = pd.read_csv(
    "OR-Space/supporting_files/metadata/workspace_index.csv"
)
print(index.groupby(["task_type", "difficulty"]).size())
```

Participant-visible task data are organized as:

```text
OR-Space/
├── workspace_benchmark/
│   ├── build/
│   ├── revise/
│   └── explain/
├── evaluation/
│   ├── build_evaluation/
│   ├── revise_evaluation/
│   └── explain_evaluation/
├── evaluation_programs/
└── supporting_files/
```

## Empirical difficulty

Difficulty labels are derived from real benchmark outcomes under a fixed
evaluation panel, separately for each task. Build and Revise use empirical
executable pass rates; Explain uses the empirical mean rubric score. Boundaries
approximate tertiles without splitting tied scores. The released distributions
are Build 35/32/33, Revise 39/30/31, and Explain 33/33/34 for
Easy/Medium/Hard. See
[`benchmark_metadata/difficulty_methodology.md`](benchmark_metadata/difficulty_methodology.md)
and [`benchmark_metadata/empirical_difficulty.csv`](benchmark_metadata/empirical_difficulty.csv).

## Evaluation and results

[`evaluation/`](evaluation/) provides runnable scorers. The Explain release
includes normalized exact checks, semantic checklist judgments, evidence
verification, the judge prompt and schema, and the final 35/35/20/10 rubric
with an unsupported-claim penalty of up to 12 points.

[`results/table2_main_results.csv`](results/table2_main_results.csv) is the
18-model main-table snapshot. Its Revise-code values are preserved exactly as
reported. Because several released Revise rows use conservative repeated runs
or infrastructure recovery rather than an ordinary first call, consult
[`baseline_outputs/gurobi/revise_code_protocol.csv`](baseline_outputs/gurobi/revise_code_protocol.csv)
before interpreting that column as Pass@1.

## Validation

```bash
python tools/validate_public_release.py
python -m unittest discover -s tests
```

The validator checks paper-table alignment, difficulty metadata, model-archive
coverage, Revise provenance, checksums, and accidental credentials.

## Citation

```bibtex
@misc{zhou2026orspace,
  title = {OR-Space: A Full-Lifecycle Workspace Benchmark for Industrial Optimization Agents},
  author = {Zhou, Chenyu and Lu, Xinyun and Zhao, Jiangyue and Lin, Jianghao and Ge, Dongdong and Ye, Yinyu},
  year = {2026},
  note = {Dataset: https://huggingface.co/datasets/Chenyu-Zhou/OR-Space}
}
```

## License

The release is for non-commercial research use under CC BY-NC 4.0-compatible
terms, following the inherited license constraints of the IndustryOR seed
topologies. Proprietary solver binaries, commercial credentials, and
third-party model services are not redistributed.
