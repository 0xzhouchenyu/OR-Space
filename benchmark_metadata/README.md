# Benchmark metadata

This directory mirrors the public benchmark index and empirical difficulty
metadata distributed with the participant workspaces.

| File | Purpose |
| --- | --- |
| `workspace_index.csv` | One row for each of the 300 task views |
| `empirical_difficulty.csv` | Task-specific empirical score, rank, and difficulty label |
| `difficulty_methodology.md` | Signal definitions and tie-preserving partition rule |
| `schema.md` | Field definitions |
| `provenance.md` | Source and release provenance |

Difficulty is calculated from released benchmark evaluations under the fixed
18-model Gurobi panel represented in `baseline_outputs/gurobi/`. This repository
therefore exposes both the derived labels and the model-run evidence from which
they were computed. Participant workspaces use the same labels in their local
`metadata.json` files.
