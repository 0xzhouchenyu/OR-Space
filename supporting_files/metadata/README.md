# Metadata

- `workspace_index.csv`: participant-safe index of all 300 task views. It
  contains task inputs and paths, but no objectives, checklists, or reference
  answers.
- `empirical_difficulty.csv`: per-instance empirical performance, rank, and
  derived Easy/Medium/Hard label.
- `difficulty_methodology.md`: the task-specific metric and tie-preserving
  partition rule used for difficulty.
- `schema.md`: field and workspace schemas.

Evaluator-only labels are stored separately under `evaluation/`.
