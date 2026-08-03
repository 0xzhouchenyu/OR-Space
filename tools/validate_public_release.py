#!/usr/bin/env python3
"""Validate OR-Space paper snapshots, Explain rubrics, and staged workspaces."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any


SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"(?i)(api[_-]?key|password|secret)\s*[:=]\s*['\"][^'\"]+"),
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def validate_results(repo: Path, errors: list[str]) -> None:
    with (repo / "results/table2_main_results.csv").open(newline="", encoding="utf-8") as handle:
        main = list(csv.DictReader(handle))
    with (repo / "results/gurobi/revise_code.csv").open(newline="", encoding="utf-8") as handle:
        revise = list(csv.DictReader(handle))
    if len(main) != 18 or len(revise) != 18:
        errors.append(f"Expected 18 Table 2 rows; main={len(main)}, revise={len(revise)}")
    main_by_model = {row["model"]: row for row in main}
    if len(main_by_model) != len(main):
        errors.append("Duplicate model in Table 2 snapshot")
    for row in revise:
        model = row["model"]
        if model not in main_by_model:
            errors.append(f"Revise snapshot model missing from Table 2: {model}")
            continue
        expected = float(main_by_model[model]["revise_code_gurobi_pass_at_1_percent"])
        observed = float(row["pass_at_1_percent"])
        if expected != observed:
            errors.append(f"Revise/Table 2 mismatch for {model}: {observed} != {expected}")
        if int(row["total"]) != 100 or int(row["passed"]) != int(observed):
            errors.append(f"Invalid 100-instance aggregate for {model}")

    with (repo / "baseline_outputs/gurobi/model_index.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        archives = list(csv.DictReader(handle))
    with (repo / "baseline_outputs/gurobi/revise_code_protocol.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        protocol = list(csv.DictReader(handle))
    if len(archives) != 2 or len(protocol) != 18:
        errors.append(
            f"Expected 2 public archives and 18 protocol rows; archives={len(archives)}, "
            f"protocol={len(protocol)}"
        )
    archive_by_model = {row["paper_model"]: row for row in archives}
    protocol_by_model = {row["paper_model"]: row for row in protocol}
    if set(archive_by_model) != {"gpt-5.4", "deepseek-v4-flash"}:
        errors.append(f"Unexpected public Gurobi archive set: {sorted(archive_by_model)}")
    if set(protocol_by_model) != set(main_by_model):
        errors.append("Revise protocol and Table 2 model sets differ")
    expected_status = {
        "gemini-3.1-pro": "not_pass_at_1",
        "claude-opus-4-6": "not_pass_at_1",
        "claude-sonnet-4.5": "not_pass_at_1",
        "gemini-3-flash": "recovery_composite",
    }
    for model, table_row in main_by_model.items():
        if model not in protocol_by_model:
            continue
        audit = protocol_by_model[model]
        published = float(table_row["revise_code_gurobi_pass_at_1_percent"])
        if float(audit["published_revise_score"]) != published:
            errors.append(f"Revise protocol/Table 2 mismatch for {model}")
        if model in archive_by_model and audit["release_mode"] != archive_by_model[model]["revise_release_mode"]:
            errors.append(f"Revise release mode mismatch for {model}")
        expected = expected_status.get(model, "pass_at_1")
        if audit["pass_at_1_status"] != expected:
            errors.append(f"Unexpected Revise protocol status for {model}")

    for model, archive in archive_by_model.items():
        archive_path = repo / "baseline_outputs/gurobi" / archive["archive"]
        if not archive_path.is_file():
            errors.append(f"Missing public archive for {model}")
            continue
        digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        if digest != archive["archive_sha256"]:
            errors.append(f"Archive checksum mismatch for {model}")
            continue
        with zipfile.ZipFile(archive_path) as bundle:
            broken = bundle.testzip()
            if broken:
                errors.append(f"Corrupt member in {model} archive: {broken}")
                continue
            prefix = f"{model}/explain/"
            results = json.loads(bundle.read(prefix + "results.json"))
            if len(results) != 100 or {row["id"] for row in results} != set(range(1, 101)):
                errors.append(f"Incomplete Explain result rows for {model}")
            unfinished = [row["id"] for row in results if row.get("finish_reason") != "stop"]
            if unfinished:
                errors.append(f"Non-complete Explain responses for {model}: {unfinished}")
            names = set(bundle.namelist())
            for directory, suffix in (("raw", "txt"), ("answers", "txt"), ("scores", "json")):
                missing = [
                    instance_id
                    for instance_id in range(1, 101)
                    if f"{prefix}{directory}/instance_{instance_id}.{suffix}" not in names
                ]
                if missing:
                    errors.append(f"Missing Explain {directory} files for {model}: {missing}")


def validate_benchmark_metadata(repo: Path, errors: list[str]) -> None:
    metadata = repo / "benchmark_metadata"
    with (metadata / "workspace_index.csv").open(newline="", encoding="utf-8") as handle:
        index = list(csv.DictReader(handle))
    with (metadata / "empirical_difficulty.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        difficulty = list(csv.DictReader(handle))
    if len(index) != 300 or len(difficulty) != 300:
        errors.append(
            f"Expected 300 workspace/difficulty rows; index={len(index)}, "
            f"difficulty={len(difficulty)}"
        )
        return
    expected = {
        "build": {"Easy": 35, "Medium": 32, "Hard": 33},
        "revise": {"Easy": 39, "Medium": 30, "Hard": 31},
        "explain": {"Easy": 33, "Medium": 33, "Hard": 34},
    }
    observed: dict[str, Counter[str]] = {}
    for row in difficulty:
        observed.setdefault(row["task_type"], Counter())[row["difficulty"]] += 1
    for task, counts in expected.items():
        if dict(observed.get(task, Counter())) != counts:
            errors.append(f"Unexpected {task} difficulty distribution: {dict(observed.get(task, {}))}")
    index_labels = {
        row["workspace_id"]: row.get("difficulty") for row in index
    }
    for row in difficulty:
        if index_labels.get(row["workspace_id"]) != row["difficulty"]:
            errors.append(f"Difficulty/index mismatch for {row['workspace_id']}")


def validate_rubrics(path: Path, errors: list[str]) -> None:
    rows = load_jsonl(path)
    if len(rows) != 100:
        errors.append(f"Expected 100 Explain rubrics, found {len(rows)}")
    ids = [row.get("instance_id") for row in rows]
    if len(set(ids)) != len(ids):
        errors.append("Duplicate Explain rubric instance_id")
    types = Counter()
    entities = 0
    for row in rows:
        checklist = row.get("checklist")
        if not isinstance(checklist, list) or not checklist:
            errors.append(f"Missing checklist for {row.get('instance_id')}")
            continue
        for item in checklist:
            kind = item.get("checklist_type")
            types[kind] += 1
            if kind == "exact_match":
                targets = item.get("target_entities")
                if not isinstance(targets, list) or not targets:
                    errors.append(f"Empty exact targets for {row.get('instance_id')}")
                else:
                    entities += len(targets)
            elif kind == "llm_boolean_judgment":
                if not item.get("instruction_for_judge"):
                    errors.append(f"Missing judge instruction for {row.get('instance_id')}")
            else:
                errors.append(f"Unknown checklist type {kind!r}")
    if types != Counter({"exact_match": 200, "llm_boolean_judgment": 197}):
        errors.append(f"Unexpected checklist counts: {dict(types)}")
    if entities != 1011:
        errors.append(f"Expected 1,011 exact entities, found {entities}")


def validate_participant(root: Path, errors: list[str]) -> None:
    for task, directory in {
        "build": "build_workspaces", "revise": "revise_workspaces", "explain": "explain_workspaces"
    }.items():
        instances = list((root / directory).glob("instance_*"))
        if len(instances) != 100:
            errors.append(f"Expected 100 staged {task} instances, found {len(instances)}")
    for instance in (root / "build_workspaces").glob("instance_*"):
        names = {path.name for path in (instance / "src").glob("*") if path.is_file()}
        if names - {".gitkeep"} or (instance / "_agent_solution.py").exists():
            errors.append(f"Build reference code leaked in {instance.name}")
    for instance in (root / "revise_workspaces").glob("instance_*"):
        original = {path.name for path in (instance / "original/src").glob("*") if path.is_file()}
        allowed = {
            "current_heuristic.py", "utils.py", "gurobi_pulp_compat.py", "gurobi_execution_record.py"
        }
        if original - allowed or "formulation.tex" in original:
            errors.append(f"Revise-code visibility mismatch in {instance.name}: {sorted(original)}")
        revised = {path.name for path in (instance / "revised/src").glob("*") if path.is_file()}
        if revised - {".gitkeep"}:
            errors.append(f"Revised reference code leaked in {instance.name}")
    for instance in (root / "explain_workspaces").glob("instance_*"):
        metadata = json.loads((instance / "metadata.json").read_text(encoding="utf-8"))
        serialized = json.dumps(metadata).casefold()
        if "ground_truth_checklist" in serialized or "expected_short_answer" in serialized:
            errors.append(f"Explain evaluation labels leaked in participant metadata: {instance.name}")
    manifest_path = root / "release_metadata/staging_manifest.json"
    if not manifest_path.is_file():
        errors.append("Missing staging manifest")
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("revise_view") != "revise-code":
        errors.append("Staging manifest is not revise-code")
    for record in manifest.get("files", []):
        path = root / record["path"]
        if not path.is_file():
            errors.append(f"Manifest file missing: {record['path']}")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != record["sha256"]:
            errors.append(f"Manifest hash mismatch: {record['path']}")


def scan_secrets(root: Path, errors: list[str]) -> None:
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            errors.append(f"Possible credential in {path.relative_to(root)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--rubrics", type=Path)
    parser.add_argument("--participant-root", type=Path)
    args = parser.parse_args()
    errors: list[str] = []
    validate_results(args.repo, errors)
    validate_benchmark_metadata(args.repo, errors)
    scan_secrets(args.repo, errors)
    if args.rubrics:
        validate_rubrics(args.rubrics, errors)
    if args.participant_root:
        validate_participant(args.participant_root, errors)
        scan_secrets(args.participant_root, errors)
    if errors:
        print("Release validation FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Release validation PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
