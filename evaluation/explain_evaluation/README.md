# Explain Rubrics

This directory contains the complete evaluator-only labels for all 100 Explain
instances.

- `rubrics.jsonl`: questions, capability dimension, multi-hop evidence path,
  exact entities, semantic criteria, criterion-specific judge instructions,
  and concise expected answers.
- `judge_prompt.md`: stable system prompt for the independent rubric judge.
- `normalization.md`: deterministic exact-entity matching rules.
- `rubric_schema.json`: JSON Schema for one `rubrics.jsonl` row.

The 100 rubrics contain 397 checklist items: 200 `exact_match` items and 197
`llm_boolean_judgment` items. The exact-match items contain 1,011 atomic target
entities. Every semantic item has an explicit hit condition.

These files are evaluation labels. Do not expose this directory to the model
under evaluation. Each participant workspace contains a sanitized `metadata.json`
with the question but without the checklist or reference answer.

The checklist is the authoritative scoring target. `expected_short_answer` is
an audit aid and concise content reference; it is not defined as a guaranteed
100-point response and can omit names that the exhaustive checklist requests.

Runnable preparation, judge, and aggregation scripts are in
[`evaluation_programs/explain/`](../../evaluation_programs/explain/).
