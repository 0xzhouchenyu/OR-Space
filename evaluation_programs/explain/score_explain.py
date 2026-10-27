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
                    "criterion_id": str(item.get("criterion_id") or f"c{index}"),
                    "entity_id": f"{item.get('criterion_id') or f'c{index}'}.e{entity_index}",
                    "entity": text,
                    "hit": int(entity_hit(answer, text)),
                }
            )
    return rows


PROTOCOL_VERSION = "orspace-explain-appendix-c-v2"
GROUNDING_KEYS = (
    "code_or_model_structure", "data_or_numeric_evidence",
    "solver_record_evidence", "business_or_formulation_link",
)
QUALITY_KEYS = ("directness", "causal_explanation", "organization", "internal_consistency")
REASONING_LIMITS = {"sub_coverage": 1, "sub_causality": 1, "sub_grounding": 1, "sub_depth": 2}
PENALTIES = {"none": 0, "minor": 5, "material": 12, "severe": 20}


def _subgrade(node: Any, name: str, maximum: int) -> float:
    if not isinstance(node, dict):
        raise ValueError(f"Missing structured subgrade: {name}")
    score = node.get("score")
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise ValueError(f"{name}.score must be an integer in [0, {maximum}]")
    if not math.isfinite(score) or score != int(score) or not 0 <= score <= maximum:
        raise ValueError(f"{name}.score must be an integer in [0, {maximum}]")
    if not isinstance(node.get("evidence_quote"), str):
        raise ValueError(f"Missing {name}.evidence_quote")
    return float(score)


def _anchored_dimension(judgment: dict[str, Any], name: str, keys: tuple[str, ...],
                        maximum: float) -> float:
    dimension = judgment.get(name)
    if not isinstance(dimension, dict) or set(dimension) != set(keys):
        raise ValueError(f"{name} must contain exactly these subdimensions: {keys}")
    raw = sum(_subgrade(dimension[key], f"{name}.{key}", 3) for key in keys)
    return raw / 12.0 * maximum


def score_one(
    rubric: dict[str, Any], answer_row: dict[str, Any], judgment: dict[str, Any]
) -> dict[str, Any]:
    if not isinstance(judgment, dict):
        raise ValueError("Judge output must be an object")
    if "llm_boolean_judgments" in judgment or "hallucination_penalty" in judgment:
        raise ValueError("Obsolete judge output: use the Appendix C structured protocol")
    if judgment.get("protocol_version", PROTOCOL_VERSION) != PROTOCOL_VERSION:
        raise ValueError("Judge protocol_version does not match this scorer")
    if not isinstance(judgment.get("notes"), str):
        raise ValueError("Judge output is missing notes")
    answer = str(answer_row.get("answer") or "")
    exact = exact_results(answer, rubric)
    checklist = rubric.get("checklist") or []
    semantic_items = {
        str(item.get("criterion_id") or f"c{index}"): item
        for index, item in enumerate(checklist, 1)
        if item.get("checklist_type") == "llm_boolean_judgment"
    }
    if len(semantic_items) != sum(item.get("checklist_type") == "llm_boolean_judgment"
                                  for item in checklist):
        raise ValueError("Duplicate semantic criterion IDs in rubric")
    raw_items = judgment.get("reasoning_items")
    if not isinstance(raw_items, list):
        raise ValueError("Judge output is missing reasoning_items")
    items_by_id: dict[str, dict[str, Any]] = {}
    for item in raw_items:
        if not isinstance(item, dict):
            raise ValueError("Each reasoning item must be an object")
        criterion_id = item.get("criterion_id")
        # Historical v2 records use a zero-based index into the full checklist.
        index = item.get("criterion_index")
        if index is not None:
            if type(index) is not int or not 0 <= index < len(checklist):
                raise ValueError(f"Invalid criterion_index: {index!r}")
            indexed_id = str(checklist[index].get("criterion_id") or f"c{index + 1}")
            if criterion_id is not None and criterion_id != indexed_id:
                raise ValueError("Conflicting criterion_id and criterion_index")
            criterion_id = indexed_id
        if (not isinstance(criterion_id, str) or criterion_id not in semantic_items
                or criterion_id in items_by_id):
            raise ValueError(f"Unknown or duplicate semantic criterion: {criterion_id!r}")
        for key, maximum in REASONING_LIMITS.items():
            _subgrade(item.get(key), f"{criterion_id}.{key}", maximum)
        items_by_id[criterion_id] = item
    missing = set(semantic_items) - set(items_by_id)
    if missing:
        raise ValueError(f"Missing reasoning items: {sorted(missing)}")
    reasoning_items = []
    for criterion_id in semantic_items:
        item = items_by_id[criterion_id]
        values = {key: float(item[key]["score"]) for key in REASONING_LIMITS}
        item_score = (values["sub_coverage"] + values["sub_causality"]
                      + values["sub_grounding"] + values["sub_depth"] / 2.0) / 4.0
        reasoning_items.append({**item, "criterion_id": criterion_id, "item_score": item_score})
    # Empty components follow the historical v2 convention; released rubrics
    # all contain exact entities and at least one semantic item.
    hits = sum(item["hit"] for item in exact)
    coverage = 35.0 * hits / len(exact) if exact else 35.0
    reasoning = (35.0 * sum(item["item_score"] for item in reasoning_items)
                 / len(reasoning_items) if reasoning_items else 35.0)
    grounding = _anchored_dimension(judgment, "grounding", GROUNDING_KEYS, 20.0)
    quality = _anchored_dimension(judgment, "answer_quality", QUALITY_KEYS, 10.0)
    hallucination = judgment.get("hallucination")
    if not isinstance(hallucination, dict):
        raise ValueError("Judge output is missing hallucination")
    level = hallucination.get("level")
    claims = hallucination.get("unsupported_claims")
    if not isinstance(level, str) or level not in PENALTIES:
        raise ValueError(f"Invalid hallucination level: {level!r}")
    if not isinstance(claims, list) or any(not isinstance(c, str) or not c.strip() for c in claims):
        raise ValueError("unsupported_claims must be a list of nonempty quoted strings")
    if not claims:
        level = "none"
    elif level == "none":
        raise ValueError("Nonempty unsupported_claims require a positive penalty level")
    penalty = PENALTIES[level]
    total = max(0.0, min(100.0, coverage + reasoning + grounding + quality - penalty))
    return {
        "instance_id": rubric["instance_id"],
        "workspace_id": rubric["workspace_id"],
        "protocol_version": PROTOCOL_VERSION,
        "score": total,
        "dimensions": {
            "exact_coverage": coverage, "reasoning": reasoning,
            "grounding": grounding, "answer_quality": quality,
            "hallucination_penalty": penalty,
        },
        "coverage": {"hits": hits, "total": len(exact)},
        "exact_match_results": exact,
        "reasoning_items": reasoning_items,
        "grounding": judgment["grounding"],
        "answer_quality": judgment["answer_quality"],
        "hallucination": {**hallucination, "level": level},
        "notes": judgment["notes"],
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
        "protocol_version": PROTOCOL_VERSION,
        "scored_instances": len(scored),
        "rubric_instances": len(rubrics),
        "rubric_mean": mean,
    }
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
