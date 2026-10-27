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

The scoring specification follows the article's Appendix C and P6:
Exact Coverage uses only exact entities; semantic subgrades form Reasoning;
Grounding and Answer Quality use four anchored subdimensions each; hallucination
levels map to 0/5/12/20 points. The synchronized judge prompt is shared with
`evaluation_programs/explain/`; its JSON schema is
[`judgment_schema.json`](../../evaluation_programs/explain/judgment_schema.json).
The superseded boolean-plus-aggregate protocol is not the paper metric.
Reported benchmark scores remain those in the OR-Space article.
