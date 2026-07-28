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
REQUIRED_CATALOG_COLUMNS = {
    "instance_id",
    "benchmark_instance_id",
    "revise_instance_id",
    "difficulty",
    "revise_type",
    "revise_type_name",
    "tolerance",
    "workspace_sha256",
}
REQUIRED_PER_INSTANCE_COLUMNS = {
    "paper_model",
    "artifact_model",
    "instance_id",
    "benchmark_instance_id",
    "workspace_sha256",
    "attempt_1_status",
    "attempt_1_passed",
    "attempt_1_extracted_value",
    "attempt_1_row_sha256",
    "attempt_1_artifact_sha256",
    "attempt_1_source",
    "attempt_2_status",
    "attempt_2_passed",
    "attempt_2_extracted_value",
    "attempt_2_row_sha256",
    "attempt_2_artifact_sha256",
    "attempt_2_source",
    "attempt_2_policy",
    "pass_at_1",
    "pass_both_at_2",
    "conditional_resample_status",
    "conditional_resample_passed",
    "conditional_resample_temperature",
    "conditional_resample_row_sha256",
    "conditional_resample_artifact_sha256",
    "conditional_resample_source",
    "evidence_status",
    "note",
}
BOOL_TEXT = {"", "true", "false"}
REQUIRED_PASS_BOTH_COLUMNS = {
    "paper_model",
    "artifact_model",
    "attempt_1_passed",
    "repeated_first_passes",
    "repeat_failures",
    "pass_both_at_2_passed",
    "total",
    "pass_both_at_2_percent",
    "attempt_2_temperature",
    "matches_table2_snapshot",
    "per_instance_public_evidence",
    "source",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def validate(root: Path, allow_provisional: bool) -> list[str]:
    errors: list[str] = []
    manifest_path = root / "release_manifest.json"
    snapshot_path = root / "table2_snapshot.csv"
    provenance_path = root / "provenance_review.csv"
    catalog_path = root / "per_instance" / "instance_catalog.csv"
    per_instance_path = root / "per_instance" / "results.csv"
    schema_path = root / "per_instance" / "schema.json"
    pass_both_path = root / "pass_both_at_2_available.csv"
    for path in (
        manifest_path,
        snapshot_path,
        provenance_path,
        catalog_path,
        per_instance_path,
        schema_path,
        pass_both_path,
    ):
        if not path.is_file():
            errors.append(f"missing required file: {path}")
    if errors:
        return errors

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    snapshot = read_csv(snapshot_path)
    provenance = read_csv(provenance_path)
    catalog = read_csv(catalog_path)
    per_instance = read_csv(per_instance_path)
    pass_both = read_csv(pass_both_path)

    if not snapshot:
        errors.append("table2_snapshot.csv is empty")
        return errors
    if set(snapshot[0]) != REQUIRED_SNAPSHOT_COLUMNS:
        errors.append("table2_snapshot.csv columns do not match the schema")
    if not provenance or set(provenance[0]) != REQUIRED_PROVENANCE_COLUMNS:
        errors.append("provenance_review.csv columns do not match the schema")
    if not catalog or set(catalog[0]) != REQUIRED_CATALOG_COLUMNS:
        errors.append("instance_catalog.csv columns do not match the schema")
    if not per_instance or set(per_instance[0]) != REQUIRED_PER_INSTANCE_COLUMNS:
        errors.append("per_instance/results.csv columns do not match the schema")
    if not pass_both or set(pass_both[0]) != REQUIRED_PASS_BOTH_COLUMNS:
        errors.append("pass_both_at_2_available.csv columns do not match the schema")

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

    expected_instances = int(manifest["expected_instances_per_model"])
    catalog_ids = [int(row["instance_id"]) for row in catalog]
    if len(catalog) != expected_instances:
        errors.append(
            f"expected {expected_instances} catalog rows, found {len(catalog)}"
        )
    if set(catalog_ids) != set(range(1, expected_instances + 1)):
        errors.append("instance catalog must contain ids 1..100 exactly once")
    if len(catalog_ids) != len(set(catalog_ids)):
        errors.append("duplicate instance_id in instance_catalog.csv")
    catalog_by_id = {int(row["instance_id"]): row for row in catalog}

    expected_matrix_rows = expected_models * expected_instances
    if len(per_instance) != expected_matrix_rows:
        errors.append(
            f"expected {expected_matrix_rows} per-instance rows, "
            f"found {len(per_instance)}"
        )
    matrix_keys: list[tuple[str, int]] = []
    per_model_ids: dict[str, set[int]] = {}
    for row in per_instance:
        model = row["paper_model"]
        instance_id = int(row["instance_id"])
        matrix_keys.append((model, instance_id))
        per_model_ids.setdefault(model, set()).add(instance_id)
        if model not in set(snapshot_models):
            errors.append(f"unknown per-instance paper_model: {model}")
            continue
        if instance_id not in catalog_by_id:
            errors.append(f"{model}: unknown instance id {instance_id}")
            continue
        catalog_row = catalog_by_id[instance_id]
        if row["benchmark_instance_id"] != catalog_row["benchmark_instance_id"]:
            errors.append(f"{model}/{instance_id}: benchmark id mismatch")
        if row["workspace_sha256"] != catalog_row["workspace_sha256"]:
            errors.append(f"{model}/{instance_id}: workspace hash mismatch")
        for field in (
            "attempt_1_passed",
            "attempt_2_passed",
            "pass_at_1",
            "pass_both_at_2",
            "conditional_resample_passed",
        ):
            if row[field] not in BOOL_TEXT:
                errors.append(f"{model}/{instance_id}: invalid {field}")
        if row["pass_at_1"] != row["attempt_1_passed"]:
            errors.append(f"{model}/{instance_id}: Pass@1 disagrees with attempt 1")
        if row["pass_both_at_2"]:
            expected_both = (
                row["attempt_1_passed"] == "true"
                and row["attempt_2_passed"] == "true"
            )
            if row["pass_both_at_2"] != ("true" if expected_both else "false"):
                errors.append(
                    f"{model}/{instance_id}: PassBoth@2 must be attempt 1 AND attempt 2"
                )
            if row["attempt_2_policy"] not in {
                "all_instances",
                "first_passes_only",
            }:
                errors.append(f"{model}/{instance_id}: missing attempt-2 policy")
    if len(matrix_keys) != len(set(matrix_keys)):
        errors.append("duplicate model/instance rows in per_instance/results.csv")
    for model in snapshot_models:
        if per_model_ids.get(model, set()) != set(range(1, expected_instances + 1)):
            errors.append(f"{model}: per-instance ids are incomplete")

    snapshot_by_model = {row["paper_model"]: row for row in snapshot}
    for row in pass_both:
        model = row["paper_model"]
        first_passed = int(row["attempt_1_passed"])
        repeats = int(row["repeated_first_passes"])
        repeat_failures = int(row["repeat_failures"])
        both_passed = int(row["pass_both_at_2_passed"])
        total = int(row["total"])
        percent = float(row["pass_both_at_2_percent"])
        if repeats != first_passed:
            errors.append(f"{model}: not every first pass was repeated")
        if both_passed != first_passed - repeat_failures:
            errors.append(f"{model}: PassBoth@2 count is not the intersection")
        if abs(percent - 100.0 * both_passed / total) > 1e-9:
            errors.append(f"{model}: PassBoth@2 percentage is inconsistent")
        expected_match = (
            model in snapshot_by_model
            and int(snapshot_by_model[model]["passed"]) == both_passed
        )
        if row["matches_table2_snapshot"] != (
            "true" if expected_match else "false"
        ):
            errors.append(f"{model}: Table 2 match flag is incorrect")

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
    metric_semantics = manifest.get("metric_semantics", {})
    if metric_semantics.get("repeatability_rule") != (
        "attempt_1_passed AND attempt_2_passed"
    ):
        errors.append("manifest PassBoth@2 rule is missing or incorrect")
    if metric_semantics.get("table2_is_uniform_pass_both_at_2") is not False:
        errors.append("manifest must not claim current Table 2 is uniform PassBoth@2")
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
