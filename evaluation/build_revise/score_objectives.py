#!/usr/bin/env python3
"""Score OR-Space Build/Revise objective predictions."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected a JSON object")
            rows.append(value)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--references", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--task", choices=("build", "revise"))
    parser.add_argument("--allow-missing", action="store_true")
    args = parser.parse_args()

    with args.references.open(newline="", encoding="utf-8") as handle:
        references = list(csv.DictReader(handle))
    if args.task:
        references = [row for row in references if row["task_type"] == args.task]
    predictions = load_jsonl(args.predictions)
    by_id: dict[str, dict[str, Any]] = {}
    for row in predictions:
        workspace_id = str(row.get("workspace_id") or "")
        if not workspace_id or workspace_id in by_id:
            raise ValueError(f"Missing or duplicate prediction workspace_id: {workspace_id!r}")
        by_id[workspace_id] = row

    scored: list[dict[str, Any]] = []
    for ref in references:
        workspace_id = ref["workspace_id"]
        prediction = by_id.get(workspace_id)
        if prediction is None:
            if args.allow_missing:
                continue
            prediction = {"status": "Missing", "objective": None}
        status = str(prediction.get("status") or "").strip()
        objective = prediction.get("objective")
        reference = float(ref["reference_objective"])
        tolerance = float(ref.get("relative_tolerance") or 0.01)
        numeric = isinstance(objective, (int, float)) and not isinstance(objective, bool)
        relative_error = (
            abs(float(objective) - reference) / max(1.0, abs(reference))
            if numeric
            else None
        )
        passed = status.lower() == "optimal" and relative_error is not None and relative_error <= tolerance
        scored.append(
            {
                "workspace_id": workspace_id,
                "task_type": ref["task_type"],
                "solver_track": prediction.get("solver_track"),
                "status": status or "Unknown",
                "objective": float(objective) if numeric else None,
                "reference_objective": reference,
                "relative_error": relative_error,
                "relative_tolerance": tolerance,
                "passed": passed,
            }
        )

    extra = sorted(set(by_id) - {row["workspace_id"] for row in references})
    if extra:
        raise ValueError(f"Predictions contain unknown workspace ids: {extra[:5]}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for row in scored:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    counts = Counter(row["task_type"] for row in scored)
    passed = Counter(row["task_type"] for row in scored if row["passed"])
    summary = {
        "metric": "objective_match_pass_at_1",
        "tasks": {
            task: {
                "passed": passed[task],
                "total": counts[task],
                "pass_at_1_percent": 100.0 * passed[task] / counts[task] if counts[task] else 0.0,
            }
            for task in sorted(counts)
        },
    }
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
