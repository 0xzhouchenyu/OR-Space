#!/usr/bin/env python3
"""Validate the public Gurobi Revise-code snapshot and provenance review."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


REQUIRED_SNAPSHOT_COLUMNS = {
    "paper_model",
    "artifact_model",
    "group",
    "passed",
    "total",
    "pass_at_1_percent",
}
REQUIRED_PROVENANCE_COLUMNS = {
    "paper_model",
    "reported_passed",
    "evidence_passed",
    "evidence_class",
    "protocol_status",
    "public_artifacts",
    "status",
    "note",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def validate(root: Path, allow_provisional: bool) -> list[str]:
    errors: list[str] = []
    manifest_path = root / "release_manifest.json"
    snapshot_path = root / "table2_snapshot.csv"
    provenance_path = root / "provenance_review.csv"
    for path in (manifest_path, snapshot_path, provenance_path):
        if not path.is_file():
            errors.append(f"missing required file: {path}")
    if errors:
        return errors

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    snapshot = read_csv(snapshot_path)
    provenance = read_csv(provenance_path)

    if not snapshot:
        errors.append("table2_snapshot.csv is empty")
        return errors
    if set(snapshot[0]) != REQUIRED_SNAPSHOT_COLUMNS:
        errors.append("table2_snapshot.csv columns do not match the schema")
    if not provenance or set(provenance[0]) != REQUIRED_PROVENANCE_COLUMNS:
        errors.append("provenance_review.csv columns do not match the schema")

    expected_models = int(manifest["expected_models"])
    if len(snapshot) != expected_models:
        errors.append(f"expected {expected_models} snapshot rows, found {len(snapshot)}")
    if len(provenance) != expected_models:
        errors.append(f"expected {expected_models} provenance rows, found {len(provenance)}")

    snapshot_models = [row["paper_model"] for row in snapshot]
    provenance_models = [row["paper_model"] for row in provenance]
    if len(snapshot_models) != len(set(snapshot_models)):
        errors.append("duplicate paper_model in table2_snapshot.csv")
    if set(snapshot_models) != set(provenance_models):
        errors.append("snapshot and provenance model sets differ")

    provenance_by_model = {row["paper_model"]: row for row in provenance}
    for row in snapshot:
        model = row["paper_model"]
        passed = int(row["passed"])
        total = int(row["total"])
        percent = float(row["pass_at_1_percent"])
        if total != int(manifest["expected_instances_per_model"]):
            errors.append(f"{model}: expected total=100, found {total}")
        if abs(percent - 100.0 * passed / total) > 1e-9:
            errors.append(f"{model}: percentage does not match passed/total")
        if int(provenance_by_model[model]["reported_passed"]) != passed:
            errors.append(f"{model}: snapshot and provenance reported scores differ")

    statuses = {row["status"] for row in provenance}
    if not allow_provisional and statuses != {"ready"}:
        unresolved = [
            f"{row['paper_model']}={row['status']}"
            for row in provenance
            if row["status"] != "ready"
        ]
        errors.append("archival gate failed: " + ", ".join(unresolved))
    if bool(manifest.get("archival_ready")) != (statuses == {"ready"}):
        errors.append("release_manifest archival_ready disagrees with provenance statuses")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--allow-provisional", action="store_true")
    args = parser.parse_args()
    errors = validate(args.root, args.allow_provisional)
    if errors:
        print("Table 2 Gurobi Revise-code release validation FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Table 2 Gurobi Revise-code release structure is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
