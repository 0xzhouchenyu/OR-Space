# Release provenance

The workspace benchmark is derived from the 100-topology OR-Space authoring
snapshot previously published in this dataset repository. The v1.0 release
pipeline separates participant-visible artifacts from evaluator labels:

- Build reference programs and objective values are removed from participant
  workspaces.
- Revise is staged as the paper's default Revise-code view: original/revised
  documents and data plus the correct executable original heuristic and its
  utility/runtime helpers; formal-model context and revised reference source
  are withheld.
- Explain retains the validated documents, data, source, execution logs, and
  solver records for both versions, while checklists and reference answers are
  moved to `evaluation/explain_evaluation/`.

The public validator checks task counts, visibility boundaries, objective
references, rubric counts, and English-only release text.

Private evaluation infrastructure, API credentials, proprietary solver
binaries, and unrelated development files are not part of the release.
