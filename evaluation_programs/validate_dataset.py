#!/usr/bin/env python3
"""Validate the self-contained OR-Space benchmark dataset."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
TASK_DIRECTORIES = {
    "build": "build_workspaces",
    "revise": "revise_workspaces",
    "explain": "explain_workspaces",
}


def instance_dirs(task: str) -> list[Path]:
    return sorted((ROOT / "Workspace_OR" / TASK_DIRECTORIES[task]).glob("instance_*"))


def main() -> int:
    errors: list[str] = []

    for task in ("build", "revise", "explain"):
        instances = [path for path in instance_dirs(task) if path.is_dir()]
        if len(instances) != 100:
            errors.append(f"Expected 100 {task} workspaces; found {len(instances)}")

    for path in instance_dirs("build"):
        visible = [item for item in (path / "src").glob("*") if item.name != ".gitkeep"]
        if visible:
            errors.append(f"Build source is not empty: {path.name}")

    for path in instance_dirs("revise"):
        original = path / "original" / "src" / "current_heuristic.py"
        if not original.is_file():
            errors.append(f"Revise original code is missing: {path.name}")
        visible = [
            item for item in (path / "revised" / "src").glob("*") if item.name != ".gitkeep"
        ]
        if visible:
            errors.append(f"Revised reference source is visible: {path.name}")

    for path in instance_dirs("explain"):
        metadata = json.loads((path / "metadata.json").read_text(encoding="utf-8"))
        explain_task = metadata.get("explain_task", {})
        leaked = {"multi_hop_path", "llm_failure_mode_prediction"} & set(explain_task)
        if leaked or "source_json" in metadata:
            errors.append(f"Explain metadata contains internal fields: {path.name}")
        for version in ("original", "revised"):
            required = (
                path / version / "src" / "optimization_model.py",
                path / version / "logs" / "execution_record.json",
            )
            if not all(item.is_file() for item in required):
                errors.append(f"Explain evidence is incomplete: {path.name}/{version}")

    index_path = ROOT / "supporting_files" / "metadata" / "workspace_index.csv"
    with index_path.open(newline="", encoding="utf-8") as handle:
        index = list(csv.DictReader(handle))
    counts = Counter(row["task_type"] for row in index)
    if counts != Counter({"build": 100, "revise": 100, "explain": 100}):
        errors.append(f"Unexpected workspace index counts: {dict(counts)}")
    for row in index:
        if not (ROOT / row["workspace_path"]).is_dir():
            errors.append(f"Indexed workspace is missing: {row['workspace_path']}")

    difficulty_path = ROOT / "supporting_files" / "metadata" / "empirical_difficulty.csv"
    with difficulty_path.open(newline="", encoding="utf-8") as handle:
        difficulty = list(csv.DictReader(handle))
    difficulty_counts = Counter((row["task_type"], row["difficulty"]) for row in difficulty)
    expected_difficulty = Counter(
        {
            ("build", "Easy"): 35,
            ("build", "Medium"): 32,
            ("build", "Hard"): 33,
            ("revise", "Easy"): 39,
            ("revise", "Medium"): 30,
            ("revise", "Hard"): 31,
            ("explain", "Easy"): 33,
            ("explain", "Medium"): 33,
            ("explain", "Hard"): 34,
        }
    )
    if len(difficulty) != 300 or difficulty_counts != expected_difficulty:
        errors.append(f"Unexpected empirical difficulty inventory: {dict(difficulty_counts)}")
    index_by_id = {row["workspace_id"]: row for row in index}
    for row in difficulty:
        indexed = index_by_id.get(row["workspace_id"])
        field = "difficulty_level" if row["task_type"] == "explain" else "difficulty"
        if indexed is None or indexed[field] != row["difficulty"]:
            errors.append(f"Difficulty/index mismatch: {row['workspace_id']}")
        number = int(row["instance_number"])
        metadata = json.loads(
            (
                ROOT
                / "Workspace_OR"
                / TASK_DIRECTORIES[row["task_type"]]
                / f"instance_{number}"
                / "metadata.json"
            ).read_text(
                encoding="utf-8"
            )
        )
        evidence = metadata.get("difficulty_evidence", {})
        if evidence.get("label") != row["difficulty"]:
            errors.append(f"Difficulty/metadata mismatch: {row['workspace_id']}")

    for task in ("build", "revise"):
        path = ROOT / "evaluation" / f"{task}_evaluation" / "reference_objectives.csv"
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        if len(rows) != 100 or {row["task_type"] for row in rows} != {task}:
            errors.append(f"Expected 100 {task} objective references")

    rubric_path = ROOT / "evaluation" / "explain_evaluation" / "rubrics.jsonl"
    rubrics = [json.loads(line) for line in rubric_path.read_text().splitlines() if line.strip()]
    rubric_types = Counter(
        item["checklist_type"] for row in rubrics for item in row.get("checklist", [])
    )
    if len(rubrics) != 100 or rubric_types != Counter(
        {"exact_match": 200, "llm_boolean_judgment": 197}
    ):
        errors.append(f"Unexpected Explain rubric inventory: {dict(rubric_types)}")

    release_roots = (
        ROOT / "Workspace_OR",
        ROOT / "evaluation",
        ROOT / "evaluation_programs",
        ROOT / "supporting_files",
    )
    for release_root in release_roots:
        for path in release_root.rglob("*"):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if CJK.search(text):
                errors.append(f"Non-English CJK text remains in {path.relative_to(ROOT)}")

    if errors:
        print("Dataset validation FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Dataset validation PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
