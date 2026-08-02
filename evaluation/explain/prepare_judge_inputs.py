#!/usr/bin/env python3
"""Build evidence-complete OR-Space Explain judge requests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from score_explain import exact_results, load_jsonl


def read_evidence(instance_dir: Path, maximum: int) -> list[dict[str, str]]:
    evidence: list[dict[str, str]] = []
    total = 0
    for version in ("original", "revised"):
        root = instance_dir / version
        if not root.is_dir():
            raise FileNotFoundError(f"Missing Explain evidence directory: {root}")
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.name in {".DS_Store"}:
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError(f"Non-text evidence file: {path}") from exc
            total += len(content)
            if total > maximum:
                raise ValueError(
                    f"Evidence for {instance_dir.name} exceeds --max-evidence-chars={maximum}; "
                    "raise the limit instead of silently truncating it"
                )
            evidence.append({"path": str(path.relative_to(instance_dir)), "content": content})
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rubrics", type=Path, required=True)
    parser.add_argument("--answers", type=Path, required=True)
    parser.add_argument("--workspaces", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-evidence-chars", type=int, default=1_000_000)
    args = parser.parse_args()

    rubrics = load_jsonl(args.rubrics, "instance_id")
    answers = load_jsonl(args.answers, "instance_id")
    unknown = set(answers) - set(rubrics)
    if unknown:
        raise ValueError(f"Unknown answer instance ids: {sorted(unknown)[:5]}")
    missing = set(rubrics) - set(answers)
    if missing:
        raise ValueError(f"Missing answers: {sorted(missing)[:5]}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for rubric in rubrics.values():
            instance_number = int(rubric["instance_number"])
            instance_id = rubric["instance_id"]
            answer = str(answers[instance_id].get("answer") or "")
            payload: dict[str, Any] = {
                "instance_id": instance_id,
                "question": rubric["question"],
                "answer": answer,
                "checklist": rubric["checklist"],
                "exact_match_results": exact_results(answer, rubric),
                "verified_evidence": read_evidence(
                    args.workspaces / f"instance_{instance_number}", args.max_evidence_chars
                ),
            }
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"Wrote {len(rubrics)} judge inputs to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

