#!/usr/bin/env python3
"""Score OR-Space Explain answers from public rubrics and judge decisions."""

from __future__ import annotations

import argparse
import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Any


def load_jsonl(path: Path, key: str) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected a JSON object")
            row_id = str(value.get(key) or "")
            if not row_id or row_id in rows:
                raise ValueError(f"{path}:{line_number}: missing or duplicate {key}: {row_id!r}")
            rows[row_id] = value
    return rows


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value)
    replacements = {
        "“": '"', "”": '"', "‘": "'", "’": "'", "−": "-", "–": "-",
        "—": "-", "→": "->", "⇒": "->", "←": "<-", "⇐": "<-",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.replace("`", "")
    text = re.sub(r"(?<=\d),(?=\d{3}(?:\D|$))", "", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def compact_symbol(value: str) -> str:
    text = normalize_text(value)
    text = text.replace("[", "(").replace("]", ")")
    return re.sub(r"[\s\"']+", "", text)


def _as_number(value: str) -> float | None:
    candidate = normalize_text(value).replace(",", "")
    if not re.fullmatch(r"[-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?", candidate):
        return None
    try:
        number = float(candidate)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def entity_hit(answer: str, entity: str) -> bool:
    normalized_answer = normalize_text(answer)
    normalized_entity = normalize_text(entity)
    identifier = bool(re.fullmatch(r"[a-z0-9_]+", normalized_entity))
    if identifier:
        pattern = rf"(?<![a-z0-9_]){re.escape(normalized_entity)}(?![a-z0-9_])"
        if re.search(pattern, normalized_answer):
            return True
    elif normalized_entity and normalized_entity in normalized_answer:
        return True
    if not identifier:
        compact_entity = compact_symbol(entity)
        if compact_entity and compact_entity in compact_symbol(answer):
            return True
    expected_number = _as_number(entity)
    if expected_number is not None:
        for token in re.findall(r"[-+]?\d[\d,]*(?:\.\d+)?(?:e[-+]?\d+)?", answer, re.I):
            try:
                observed = float(token.replace(",", ""))
            except ValueError:
                continue
            if math.isclose(observed, expected_number, rel_tol=1e-6, abs_tol=1e-9):
                return True
    return False


def exact_results(answer: str, rubric: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(rubric.get("checklist") or [], 1):
        if item.get("checklist_type") != "exact_match":
            continue
        for entity_index, entity in enumerate(item.get("target_entities") or [], 1):
            text = str(entity)
            rows.append(
                {
                    "criterion_id": f"c{index}",
                    "entity_id": f"c{index}.e{entity_index}",
                    "entity": text,
                    "hit": int(entity_hit(answer, text)),
                }
            )
    return rows


def _dimension(judgment: dict[str, Any], name: str, maximum: float) -> float:
    value = judgment.get(name)
    if not isinstance(value, dict) or not isinstance(value.get("score"), (int, float)):
        raise ValueError(f"Judge output is missing numeric {name}.score")
    score = float(value["score"])
    if not 0.0 <= score <= maximum:
        raise ValueError(f"{name}.score={score} is outside [0, {maximum}]")
    return score


def score_one(
    rubric: dict[str, Any], answer_row: dict[str, Any], judgment: dict[str, Any]
) -> dict[str, Any]:
    answer = str(answer_row.get("answer") or "")
    exact = exact_results(answer, rubric)
    semantic_items = {
        f"c{index}": item
        for index, item in enumerate(rubric.get("checklist") or [], 1)
        if item.get("checklist_type") == "llm_boolean_judgment"
    }
    raw_booleans = judgment.get("llm_boolean_judgments")
    if not isinstance(raw_booleans, list):
        raise ValueError("Judge output is missing llm_boolean_judgments")
    boolean_by_id: dict[str, dict[str, Any]] = {}
    for value in raw_booleans:
        if not isinstance(value, dict):
            raise ValueError("Each semantic judgment must be an object")
        criterion_id = str(value.get("criterion_id") or "")
        hit = value.get("hit")
        if criterion_id in boolean_by_id or criterion_id not in semantic_items or hit not in (0, 1):
            raise ValueError(f"Invalid or duplicate semantic judgment: {value!r}")
        boolean_by_id[criterion_id] = value
    missing = sorted(set(semantic_items) - set(boolean_by_id))
    extra = sorted(set(boolean_by_id) - set(semantic_items))
    if missing or extra:
        raise ValueError(f"Semantic judgments do not match rubric; missing={missing}, extra={extra}")

    boolean_results = [
        {
            "criterion_id": criterion_id,
            "criterion": semantic_items[criterion_id].get("criterion"),
            "hit": int(boolean_by_id[criterion_id]["hit"]),
            "reason": str(boolean_by_id[criterion_id].get("reason") or ""),
        }
        for criterion_id in sorted(boolean_by_id, key=lambda value: int(value[1:]))
    ]
    atomic_total = len(exact) + len(boolean_results)
    atomic_hits = sum(row["hit"] for row in exact) + sum(row["hit"] for row in boolean_results)
    coverage = 35.0 * atomic_hits / atomic_total if atomic_total else 35.0
    reasoning = _dimension(judgment, "reasoning", 35.0)
    grounding = _dimension(judgment, "grounding", 20.0)
    quality = _dimension(judgment, "answer_quality", 10.0)
    penalty = _dimension(judgment, "hallucination_penalty", 20.0)
    total = max(0.0, min(100.0, coverage + reasoning + grounding + quality - penalty))
    return {
        "instance_id": rubric["instance_id"],
        "workspace_id": rubric["workspace_id"],
        "score": total,
        "dimensions": {
            "exact_coverage": coverage,
            "reasoning": reasoning,
            "grounding": grounding,
            "answer_quality": quality,
            "hallucination_penalty": penalty,
        },
        "coverage": {"hits": atomic_hits, "total": atomic_total},
        "exact_match_results": exact,
        "llm_boolean_judgments": boolean_results,
        "judge_model": judgment.get("judge_model"),
        "judge_prompt_sha256": judgment.get("judge_prompt_sha256"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rubrics", type=Path, required=True)
    parser.add_argument("--answers", type=Path, required=True)
    parser.add_argument("--judgments", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--allow-missing", action="store_true")
    args = parser.parse_args()

    rubrics = load_jsonl(args.rubrics, "instance_id")
    answers = load_jsonl(args.answers, "instance_id")
    judgments = load_jsonl(args.judgments, "instance_id")
    unknown = (set(answers) | set(judgments)) - set(rubrics)
    if unknown:
        raise ValueError(f"Unknown instance ids: {sorted(unknown)[:5]}")

    scored: list[dict[str, Any]] = []
    for instance_id, rubric in rubrics.items():
        if instance_id not in answers or instance_id not in judgments:
            if args.allow_missing:
                continue
            raise ValueError(f"Missing answer or judgment for {instance_id}")
        scored.append(score_one(rubric, answers[instance_id], judgments[instance_id]))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for row in scored:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    mean = sum(row["score"] for row in scored) / len(scored) if scored else 0.0
    summary = {
        "metric": "or_space_explain_five_dimensional_rubric",
        "scored_instances": len(scored),
        "rubric_instances": len(rubrics),
        "rubric_mean": mean,
    }
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
