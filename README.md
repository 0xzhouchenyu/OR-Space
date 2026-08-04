<p align="center">
  <img src="supporting_files/assets/or_space_logo.png" width="96" alt="OR-Space logo">
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
  <img src="supporting_files/assets/or_space_overview.png" width="860" alt="Overview of the OR-Space Build, Revise, and Explain benchmark">
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

This repository is the complete research release. It contains participant
workspaces, evaluation references and programs, benchmark construction code,
and representative model-run evidence.

```text
.
├── 01_build/ ... 03_revise_business/  Benchmark construction code
├── workspace_benchmark/           Build, Revise, and Explain workspaces
├── evaluation/                    Task references and Explain rubrics
├── evaluation_programs/           Build, Revise, and Explain evaluators
├── supporting_files/              Metadata, task splits, and visual assets
├── baseline_outputs/gurobi/       Representative Gurobi traces for two models
├── tools/                         Packaging and release-validation utilities
└── tests/                         Evaluator tests
```

The public trace subset contains two representative models, `gpt-5.4` and
`deepseek-v4-flash`, with 100 Build, 100 Revise-code, and 100 Explain records
for each. Generated programs, raw responses, execution logs, answers,
stored scores, checksums, and provenance are retained where available. See
[`baseline_outputs/gurobi/`](baseline_outputs/gurobi/) for the archive structure.

## Quick start

```bash
git clone https://github.com/0xzhouchenyu/OR-Space.git
cd OR-Space
python evaluation_programs/validate_dataset.py
```

```python
import pandas as pd

index = pd.read_csv("supporting_files/metadata/workspace_index.csv")
print(index.groupby(["task_type", "difficulty"]).size())
```

The benchmark release is organized as:

```text
.
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
[`supporting_files/metadata/difficulty_methodology.md`](supporting_files/metadata/difficulty_methodology.md)
and [`supporting_files/metadata/empirical_difficulty.csv`](supporting_files/metadata/empirical_difficulty.csv).

## Evaluation and model traces

[`evaluation_programs/`](evaluation_programs/) provides runnable scorers, while
[`evaluation/`](evaluation/) contains task references and Explain rubrics. The
Explain release includes normalized exact checks, semantic checklist judgments,
evidence verification, the judge prompt and schema, and the final 35/35/20/10
rubric with an unsupported-claim penalty of up to 20 points.

Representative model traces and their release metadata are documented under
[`baseline_outputs/gurobi/`](baseline_outputs/gurobi/).

## Validation

```bash
python tools/validate_public_release.py
python evaluation_programs/validate_dataset.py
python -m unittest discover -s tests
```

The validator checks difficulty metadata, the two public model archives,
checksums, completeness, and accidental credentials.

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
