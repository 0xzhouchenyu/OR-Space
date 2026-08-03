# Explain evaluation

The Explain task uses a public, hybrid evaluator. Concrete workspace facts are
checked deterministically; an independent LLM judge handles semantic criteria
and scores reasoning, evidence grounding, answer quality, and unsupported
claims. The judge is never used for Build or Revise.

## Released labels

`explain_rubrics/rubrics.jsonl` in the Hugging Face dataset contains all 100
questions, the two checklist types, criterion-specific judge instructions,
and reference short answers. Each `exact_match` item lists required atomic
entities. Each `llm_boolean_judgment` item gives a semantic criterion and a
strict hit condition.

The release contains 397 checklist items: 200 exact-match items and 197
semantic items. The exact-match items contain 1,011 atomic entities.

## Score definition

1. Normalize the candidate answer and check every required exact entity.
2. Ask an independent judge for a binary decision on every semantic item.
3. Compute Exact Coverage over all atomic entities and semantic items with
   equal atomic weight: `35 * hits / total`.
4. The judge assigns Reasoning (0--35), Grounding (0--20), Answer Quality
   (0--10), and a Hallucination Penalty (0--12).
5. The final score is:

```text
clip(coverage + reasoning + grounding + answer_quality
     - hallucination_penalty, 0, 100)
```

The scorer recomputes coverage and the final total; it does not trust totals
returned by the judge. Missing semantic judgments are an error rather than an
implicit zero or a skipped item.

## Reproduction workflow

Prepare one JSONL answer per instance:

```json
{"instance_id":"OR_explain_001","answer":"..."}
```

After expanding the participant workspace archive, build judge inputs that
include the complete verified original/revised evidence:

```bash
python evaluation/explain/prepare_judge_inputs.py \
  --rubrics explain_rubrics/rubrics.jsonl \
  --answers answers.jsonl \
  --workspaces build-revise-explain_workspaces/explain_workspaces \
  --output judge_inputs.jsonl
```

Run an independent judge through an OpenAI-compatible endpoint:

```bash
pip install openai
python evaluation/explain/run_judge.py \
  --inputs judge_inputs.jsonl \
  --output judgments.jsonl \
  --model gpt-5.1
```

Then compute the released metric:

```bash
python evaluation/explain/score_explain.py \
  --rubrics explain_rubrics/rubrics.jsonl \
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
