# OR-Space Release Checklist

Use this checklist before publishing or tagging a new OR-Space snapshot.

## 1. Repository structure

- Confirm that participant-visible workspaces are stored under:
  - `Workspace_OR/build_workspaces/`
  - `Workspace_OR/revise_workspaces/`
  - `Workspace_OR/explain_workspaces/`
- Confirm that each task directory contains exactly 100 instances.
- Confirm that evaluator-only references are stored under:
  - `evaluation/build_evaluation/`
  - `evaluation/revise_evaluation/`
  - `evaluation/explain_evaluation/`
- Confirm that executable scorers are stored under `evaluation_programs/`.
- Confirm that metadata, splits, and visual assets are stored under
  `supporting_files/`.

## 2. Task visibility

- Build workspaces must contain business documents, data, metadata, and an
  empty `src/` scaffold. They must not contain reference implementations.
- Revise workspaces must expose the correct original Build implementation and
  its runtime helpers. The revised `src/` directory must remain empty, and
  revised reference implementations must not be participant-visible.
- Explain workspaces must contain the validated original and revised documents,
  data, source code, execution logs, and solver records. Checklists, rubrics,
  and reference answers must remain under `evaluation/explain_evaluation/`.
- The `evaluation/` directory must never be included in model-visible inputs.

## 3. Evaluation protocol

- Confirm that `reference_objectives.csv` contains 100 rows for Build and 100
  rows for Revise, with the released relative tolerance.
- Confirm that `rubrics.jsonl` contains 100 Explain rubrics.
- Confirm that the Explain judge prompt, JSON schema, and scorer consistently
  use the 35/35/20/10 rubric and a hallucination penalty of up to 20 points.
- Confirm that Build and Revise scorers require an `Optimal` status and compare
  the reported objective with the appropriate reference value.
- Confirm that documentation describes solver-specific programs rather than a
  shared PuLP model with a backend mounted by the evaluator.

## 4. Release hygiene

- Do not include model-run archives, baseline outputs, paper-result tables,
  raw model outputs, scoring traces, API credentials, or proprietary solver
  binaries.
- Confirm that all public documentation and prompts are in English.
- Check that all paths in `supporting_files/metadata/workspace_index.csv`
  resolve within the repository.
- Check that README links and images resolve from their documented locations.
- Confirm that `main` and the anonymous review branch contain the same benchmark
  files; only anonymity-specific README and release metadata may differ.

## 5. Validation

Run the complete local validation suite:

```bash
python evaluation_programs/validate_dataset.py
python tools/validate_public_release.py
python -m unittest discover -s tests -v
```

Inspect the resulting diff and confirm that no obsolete directory names remain:

```bash
git diff --check
rg -n 'workspace_benchmark|build-revise-explain_workspaces|baseline_outputs' \
  --glob '!RELEASE_CHECKLIST.md'
```

## 6. Paper synchronization

- Confirm that the paper and repository use the same workspace directory names,
  task visibility rules, objective tolerance, Explain rubric, solver API
  requirements, solver version, and execution timeout.
- Confirm that every released prompt path cited by the paper exists in the
  tagged repository snapshot.
- Confirm that the paper does not claim that model-run records or result tables
  are included in the public artifact.
- Pin an immutable commit or release tag for the camera-ready version.

## 7. Final review

- Clone the release into a clean directory and rerun all validation commands.
- Open one Build, Revise, and Explain instance and manually verify its visible
  artifacts against the task definitions.
- Review the root README, task READMEs, evaluation READMEs, and metadata
  documentation for obsolete paths or unsupported release claims.
