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

Difficulty is calculated from benchmark evaluations under a fixed 18-model
Gurobi panel. This repository releases the derived labels and a representative
two-model trace subset. Participant workspaces use the same labels in their
local `metadata.json` files.
