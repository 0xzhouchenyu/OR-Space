# Explain evaluation

The Explain task uses a public, hybrid evaluator. Concrete workspace facts are
checked deterministically; an independent LLM judge handles semantic criteria
and scores reasoning, evidence grounding, answer quality, and unsupported
claims. The judge is never used for Build or Revise.

## Released labels

`evaluation/explain_evaluation/rubrics.jsonl` contains all 100
questions, the two checklist types, criterion-specific judge instructions,
and reference short answers. Each `exact_match` item lists required atomic
entities. Each `llm_boolean_judgment` item gives a semantic criterion and a
strict hit condition.

The release contains 397 checklist items: 200 exact-match items and 197
semantic items. The exact-match items contain 1,011 atomic entities.

## Score definition

The authoritative specification is the OR-Space article, Appendix C and
Appendix E (P6). Protocol identifier: `orspace-explain-appendix-c-v2`.

1. Compute Exact Coverage **only** over required `exact_match` target entities:
   `coverage = 35 * exact_hits / exact_entities`.
2. For each semantic criterion, collect `sub_coverage`, `sub_causality`, and
   `sub_grounding` in {0, 1}, plus `sub_depth` in {0, 1, 2}. Each subgrade
   includes a verbatim candidate-answer quote. Compute
   `item = (coverage + causality + grounding + depth / 2) / 4` and
   `reasoning = 35 * mean(item)`. Semantic items do not enter Exact Coverage.
3. Grounding has four 0--3 anchored subdimensions; scale their sum from 12 to 20.
   Answer Quality has four 0--3 anchored subdimensions; scale their sum from
   12 to 10. See `judge_prompt.md` and `judgment_schema.json` for field names
   and anchors. The judge reduces a Grounding subgrade by one level (floor 0)
   if it cannot quote evidence; the returned score already includes that
   adjustment, so aggregation does not subtract it again.
4. Map hallucination levels `none/minor/material/severe` to **0/5/12/20**.
   An empty unsupported-claim list forces `none` and a zero penalty.
5. Compute `clip(coverage + reasoning + grounding + answer_quality - penalty, 0, 100)`.

All released rubrics contain exact entities and at least one semantic item.
For custom empty components, the historical v2 convention assigns the full 35
points to that component. Missing or duplicate judgments, invalid subgrades,
and obsolete aggregate-only judge outputs are errors, not silent zeros.
Canonical records identify semantic items by `criterion_id`; historical v2
records with zero-based `criterion_index` into the **full** checklist are also
accepted. Scored records retain the subgrades, evidence quotes, penalty level,
protocol version, judge identity, and prompt hash for audit.

### Migration from the obsolete public scorer

The earlier public code included semantic boolean hits in Exact Coverage,
accepted direct aggregate dimension scores, and allowed arbitrary penalties
between 0 and 20. That implementation is superseded by the article's protocol.
Old `llm_boolean_judgments`/aggregate-score records cannot be converted to the
required subgrades from totals alone and are rejected. Use stored structured
v2 judgments when available. Otherwise any new judge run requires a separately
audited experiment configuration and budget; this code update itself performs
no model calls and recomputes no reported benchmark results.

Published scores remain those reported in the OR-Space article. Updating the
implementation does not replace the paper's result tables or claim that new
endpoint calls reproduce historical scores exactly.

## Reproduction workflow

Prepare one JSONL answer per instance:

```json
{"instance_id":"OR_explain_001","answer":"..."}
```

After downloading the participant workspaces, build judge inputs that
include the complete verified original/revised evidence:

```bash
python evaluation_programs/explain/prepare_judge_inputs.py \
  --rubrics evaluation/explain_evaluation/rubrics.jsonl \
  --answers answers.jsonl \
  --workspaces Workspace_OR/explain_workspaces \
  --output judge_inputs.jsonl
```

Run an independent judge through an OpenAI-compatible endpoint:

```bash
pip install openai
python evaluation_programs/explain/run_judge.py \
  --inputs judge_inputs.jsonl \
  --output judgments.jsonl \
  --model gpt-5.1
```

Then compute the released metric locally (no API calls):

```bash
python evaluation_programs/explain/score_explain.py \
  --rubrics evaluation/explain_evaluation/rubrics.jsonl \
  --answers answers.jsonl \
  --judgments judgments.jsonl \
  --output scored.jsonl \
  --summary summary.json
```

The paper reference judge is `gpt-5.1`, run at temperature 0 with a 4,000-token
judge-output budget and up to three attempts. For comparison, report the judge
provider, exact model/version, endpoint date,
prompt hash, and dataset commit. LLM-assisted scores can drift when the judge
endpoint changes. `judge_prompt.md` and `judgment_schema.json` are the stable
public protocol; the runner requires an explicit model instead of silently
choosing one.

The judge runner validates each structured output before saving it and rejects
truncated responses. Resume refuses an existing output file with a different
protocol version, prompt hash, or judge model; use a separate output file for
a different configuration. Pin the answers, evidence, and input manifest as
well when resuming an experiment. The JSON examples above invoke paid model
services only at the explicitly shown `run_judge.py` step.
