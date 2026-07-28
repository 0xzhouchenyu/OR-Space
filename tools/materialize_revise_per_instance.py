#!/usr/bin/env python3
"""Materialize auditable per-instance Gurobi Revise-code result records.

The tool can create a transparent placeholder inventory from the 100 public
Revise-code workspaces and later populate it from immutable ``results.json``
trees. ``PassBoth@2`` is true only when both attempts pass. This is a
repeatability/consistency metric and is intentionally not called standard
Pass@2, whose conventional meaning is success in at least one of two samples.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


CATALOG_COLUMNS = (
    "instance_id",
    "benchmark_instance_id",
    "revise_instance_id",
    "difficulty",
    "revise_type",
    "revise_type_name",
    "tolerance",
    "workspace_sha256",
)

RESULT_COLUMNS = (
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
)

ARTIFACT_LAYOUT = {
    "raw": "txt",
    "code": "py",
    "stdout": "txt",
    "stderr": "txt",
    "prompts": "txt",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_row_sha256(row: dict[str, Any]) -> str:
    payload = json.dumps(
        row,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return sha256_bytes(payload)


def tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256_file(path)))
        digest.update(b"\0")
    return digest.hexdigest()


def artifact_sha256(model_dir: Path, instance_id: int) -> str:
    digest = hashlib.sha256()
    found = False
    for subdir, extension in ARTIFACT_LAYOUT.items():
        path = model_dir / subdir / f"instance_{instance_id}.{extension}"
        if not path.is_file():
            continue
        found = True
        digest.update(f"{subdir}/instance_{instance_id}.{extension}".encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256_file(path)))
        digest.update(b"\0")
    return digest.hexdigest() if found else ""


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, columns: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=columns,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def read_result_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("results") if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"{path}: expected a list of result objects")
    return rows


def normalize_rows(
    root: Path | None,
    artifact_model: str,
    expected_ids: set[int],
    *,
    allow_subset: bool = False,
) -> tuple[dict[int, dict[str, Any]], Path | None]:
    if root is None:
        return {}, None
    model_dir = root / artifact_model
    result_path = model_dir / "results.json"
    if not result_path.is_file():
        raise FileNotFoundError(f"missing result file: {result_path}")
    rows = read_result_rows(result_path)
    by_id: dict[int, dict[str, Any]] = {}
    for fallback_id, row in enumerate(rows, 1):
        instance_id = int(row.get("id", row.get("instance_id", fallback_id)))
        if instance_id in by_id:
            raise ValueError(f"{result_path}: duplicate instance id {instance_id}")
        by_id[instance_id] = row
    actual_ids = set(by_id)
    if not actual_ids <= expected_ids:
        raise ValueError(f"{result_path}: contains unexpected instance ids")
    if not allow_subset and actual_ids != expected_ids:
        missing = sorted(expected_ids - actual_ids)
        raise ValueError(f"{result_path}: missing instance ids {missing}")
    return by_id, model_dir


def bool_text(value: Any) -> str:
    if value is None or value == "":
        return ""
    return "true" if bool(value) else "false"


def result_value(row: dict[str, Any] | None, field: str) -> str:
    if row is None:
        return ""
    value = row.get(field)
    return "" if value is None else str(value)


def result_source(root: Path | None, artifact_model: str, instance_id: int) -> str:
    if root is None:
        return ""
    return f"{root.name}/{artifact_model}/results.json#instance_{instance_id}"


def catalog_from_workspaces(benchmark_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    expected_ids = set(range(1, 101))
    found_ids: set[int] = set()
    for workspace in sorted(
        benchmark_root.glob("instance_*"),
        key=lambda path: int(path.name.removeprefix("instance_")),
    ):
        instance_id = int(workspace.name.removeprefix("instance_"))
        found_ids.add(instance_id)
        metadata_path = workspace / "metadata.json"
        if not metadata_path.is_file():
            raise FileNotFoundError(f"missing metadata: {metadata_path}")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        nested = metadata.get("metadata") or {}
        rows.append(
            {
                "instance_id": instance_id,
                "benchmark_instance_id": f"IndustryOR_{instance_id}",
                "revise_instance_id": metadata.get("instance_id", ""),
                "difficulty": nested.get("difficulty", ""),
                "revise_type": metadata.get("revise_type", ""),
                "revise_type_name": metadata.get("revise_type_name", ""),
                "tolerance": metadata.get("tolerance", ""),
                "workspace_sha256": tree_sha256(workspace),
            }
        )
    if found_ids != expected_ids:
        missing = sorted(expected_ids - found_ids)
        extra = sorted(found_ids - expected_ids)
        raise ValueError(f"expected instances 1..100; missing={missing}, extra={extra}")
    return rows


def materialize_rows(
    snapshot: list[dict[str, str]],
    catalog: list[dict[str, Any]],
    *,
    attempt_1_root: Path | None = None,
    attempt_2_root: Path | None = None,
    attempt_2_policy: str = "",
    conditional_resample_root: Path | None = None,
) -> list[dict[str, Any]]:
    expected_ids = {int(row["instance_id"]) for row in catalog}
    catalog_by_id = {int(row["instance_id"]): row for row in catalog}
    if attempt_2_root is not None and attempt_1_root is None:
        raise ValueError("attempt 2 cannot be materialized without attempt 1")
    if attempt_2_root is not None and attempt_2_policy not in {
        "all_instances",
        "first_passes_only",
    }:
        raise ValueError(
            "attempt 2 requires --attempt-2-policy all_instances or "
            "first_passes_only"
        )
    output: list[dict[str, Any]] = []
    for model in snapshot:
        paper_model = model["paper_model"]
        artifact_model = model["artifact_model"]
        attempt_1, attempt_1_dir = normalize_rows(
            attempt_1_root,
            artifact_model,
            expected_ids,
        )
        attempt_2, attempt_2_dir = normalize_rows(
            attempt_2_root,
            artifact_model,
            expected_ids,
            allow_subset=attempt_2_policy == "first_passes_only",
        )
        conditional, conditional_dir = normalize_rows(
            conditional_resample_root,
            artifact_model,
            expected_ids,
            allow_subset=True,
        )
        if attempt_2_policy == "first_passes_only":
            required_second_ids = {
                instance_id
                for instance_id, row in attempt_1.items()
                if bool(row.get("passed"))
            }
            if not required_second_ids <= set(attempt_2):
                raise ValueError(
                    f"{artifact_model}: first-passes-only attempt 2 is missing "
                    f"first-attempt pass ids"
                )
            attempt_2 = {
                instance_id: attempt_2[instance_id]
                for instance_id in required_second_ids
            }

        for instance_id in sorted(expected_ids):
            catalog_row = catalog_by_id[instance_id]
            first = attempt_1.get(instance_id)
            second = attempt_2.get(instance_id)
            resample = conditional.get(instance_id)
            pass_1 = bool(first.get("passed")) if first is not None else None
            pass_both_2: bool | None = None
            if attempt_2_root is not None:
                pass_both_2 = bool(pass_1 and second and second.get("passed"))
            evidence_status = "missing"
            note = "Per-instance result artifacts are not available in this checkout."
            if first is not None:
                evidence_status = "attempt_1_complete"
                note = ""
            if pass_both_2 is not None:
                evidence_status = "pass_both_at_2_complete"
            if resample is not None and first is None:
                evidence_status = "conditional_resample_only"
                note = "Metric-excluded success-conditioned resample; not Pass@2."

            output.append(
                {
                    "paper_model": paper_model,
                    "artifact_model": artifact_model,
                    "instance_id": instance_id,
                    "benchmark_instance_id": catalog_row["benchmark_instance_id"],
                    "workspace_sha256": catalog_row["workspace_sha256"],
                    "attempt_1_status": result_value(first, "status"),
                    "attempt_1_passed": bool_text(pass_1),
                    "attempt_1_extracted_value": result_value(
                        first, "extracted_value"
                    ),
                    "attempt_1_row_sha256": (
                        canonical_row_sha256(first) if first is not None else ""
                    ),
                    "attempt_1_artifact_sha256": (
                        artifact_sha256(attempt_1_dir, instance_id)
                        if attempt_1_dir is not None
                        else ""
                    ),
                    "attempt_1_source": result_source(
                        attempt_1_root, artifact_model, instance_id
                    ),
                    "attempt_2_status": result_value(second, "status"),
                    "attempt_2_passed": bool_text(
                        bool(second.get("passed")) if second is not None else None
                    ),
                    "attempt_2_extracted_value": result_value(
                        second, "extracted_value"
                    ),
                    "attempt_2_row_sha256": (
                        canonical_row_sha256(second) if second is not None else ""
                    ),
                    "attempt_2_artifact_sha256": (
                        artifact_sha256(attempt_2_dir, instance_id)
                        if attempt_2_dir is not None and second is not None
                        else ""
                    ),
                    "attempt_2_source": (
                        result_source(attempt_2_root, artifact_model, instance_id)
                        if second is not None
                        else ""
                    ),
                    "attempt_2_policy": (
                        attempt_2_policy if pass_both_2 is not None else ""
                    ),
                    "pass_at_1": bool_text(pass_1),
                    "pass_both_at_2": bool_text(pass_both_2),
                    "conditional_resample_status": result_value(resample, "status"),
                    "conditional_resample_passed": bool_text(
                        bool(resample.get("passed")) if resample is not None else None
                    ),
                    "conditional_resample_temperature": result_value(
                        resample, "temperature"
                    )
                    or result_value(resample, "deflated_temp"),
                    "conditional_resample_row_sha256": (
                        canonical_row_sha256(resample) if resample is not None else ""
                    ),
                    "conditional_resample_artifact_sha256": (
                        artifact_sha256(conditional_dir, instance_id)
                        if conditional_dir is not None and resample is not None
                        else ""
                    ),
                    "conditional_resample_source": (
                        result_source(
                            conditional_resample_root,
                            artifact_model,
                            instance_id,
                        )
                        if resample is not None
                        else ""
                    ),
                    "evidence_status": evidence_status,
                    "note": note,
                }
            )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-root", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--catalog-out", type=Path, required=True)
    parser.add_argument("--results-out", type=Path, required=True)
    parser.add_argument("--attempt-1-root", type=Path)
    parser.add_argument("--attempt-2-root", type=Path)
    parser.add_argument(
        "--attempt-2-policy",
        choices=("all_instances", "first_passes_only"),
        default="all_instances",
    )
    parser.add_argument("--conditional-resample-root", type=Path)
    args = parser.parse_args()

    catalog = catalog_from_workspaces(args.benchmark_root)
    snapshot = read_csv(args.snapshot)
    rows = materialize_rows(
        snapshot,
        catalog,
        attempt_1_root=args.attempt_1_root,
        attempt_2_root=args.attempt_2_root,
        attempt_2_policy=(
            args.attempt_2_policy if args.attempt_2_root is not None else ""
        ),
        conditional_resample_root=args.conditional_resample_root,
    )
    write_csv(args.catalog_out, CATALOG_COLUMNS, catalog)
    write_csv(args.results_out, RESULT_COLUMNS, rows)
    completed = sum(row["evidence_status"] != "missing" for row in rows)
    print(
        json.dumps(
            {
                "instances": len(catalog),
                "model_instance_rows": len(rows),
                "rows_with_evidence": completed,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
