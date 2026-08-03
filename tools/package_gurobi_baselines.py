#!/usr/bin/env python3
"""Package the 18-model Gurobi Build/Revise/Explain baseline release.

The archives contain model outputs keyed to the participant-visible workspaces;
they intentionally do not duplicate the common docs/data inputs in every model
archive.  Build and Revise aggregates are checked against the paper Table 2
snapshot before any archive is written.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any


MODEL_MAP = {
    "gemini-3.1-pro": "gemini-3.1-pro-preview",
    "gemini-3-flash": "gemini-3-flash-preview",
    "claude-opus-4-6": "claude-opus-4-6",
    "gpt-5.4": "gpt-5.4",
    "claude-sonnet-4.5": "claude-sonnet-4.5",
    "gpt-5.1": "gpt-5.1",
    "gemini-2.5-flash": "gemini-2.5-flash",
    "gemini-2.5-pro": "gemini-2.5-pro",
    "gpt-4o": "openai_gpt-4o",
    "deepseek-v4-pro": "deepseek-v4-pro",
    "deepseek-r1-0528": "deepseek-ai_DeepSeek-R1-0528",
    "deepseek-v4-flash": "deepseek-v4-flash",
    "qwen3-max": "Qwen_Qwen3-Max",
    "qwen3-32b": "Qwen_Qwen3-32B",
    "qwen3-32b-thinking": "Qwen_Qwen3-32B-Thinking",
    "qwen3.5-27b": "qwen3.5-27b",
    "qwen3-8b": "qwen3-8b",
    "qwen3-14b": "qwen3-14b",
}

OUTPUT_DIRS = ("raw", "code", "stdout", "stderr", "prompts", "answers", "scores")
PUBLIC_FILES = ("results.json", "summary.json", "manifest.json", "merge_manifest.json")
CONSERVATIVE_CURRENT = {"gemini-3.1-pro", "claude-sonnet-4.5"}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def result_rows(path: Path) -> list[dict[str, Any]]:
    value = read_json(path)
    rows = value.get("results") if isinstance(value, dict) else value
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"{path}: expected a list of result objects")
    ids = [int(row.get("id", row.get("instance_id", index))) for index, row in enumerate(rows, 1)]
    if sorted(ids) != list(range(1, 101)):
        raise ValueError(f"{path}: expected exactly one row for every instance 1..100")
    return rows


def copy_result_tree(source: Path, destination: Path) -> None:
    if not (source / "results.json").is_file():
        raise FileNotFoundError(source / "results.json")
    destination.mkdir(parents=True, exist_ok=True)
    for name in PUBLIC_FILES:
        path = source / name
        if path.is_file():
            shutil.copy2(path, destination / name)
    for name in OUTPUT_DIRS:
        path = source / name
        if path.is_dir():
            shutil.copytree(path, destination / name)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_zip(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(candidate for candidate in source.rglob("*") if candidate.is_file()):
            info = zipfile.ZipInfo(path.relative_to(source.parent).as_posix())
            info.date_time = (2026, 8, 3, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def file_count(root: Path, subdir: str, extension: str) -> int:
    path = root / subdir
    return len(list(path.glob(f"instance_*.{extension}"))) if path.is_dir() else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current-root", type=Path, required=True)
    parser.add_argument("--revise-restored-root", type=Path, required=True)
    parser.add_argument("--revise-gemini3-root", type=Path, required=True)
    parser.add_argument("--revise-opus-conservative-root", type=Path, required=True)
    parser.add_argument("--revise-opus-second-root", type=Path, required=True)
    parser.add_argument("--build-qwen35-root", type=Path, required=True)
    parser.add_argument("--table2", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    if args.output_root.exists():
        raise FileExistsError(args.output_root)
    args.output_root.mkdir(parents=True)
    archives = args.output_root / "models"

    with args.table2.open(newline="", encoding="utf-8") as handle:
        snapshot = list(csv.DictReader(handle))
    if [row["model"] for row in snapshot] != list(MODEL_MAP):
        raise ValueError("Table 2 model order/set does not match the 18-model release map")

    index_rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="orspace-gurobi18-") as temp_name:
        temp = Path(temp_name)
        for table_row in snapshot:
            paper_model = table_row["model"]
            artifact_model = MODEL_MAP[paper_model]
            model_root = temp / paper_model

            build_source = (
                args.build_qwen35_root
                if paper_model == "qwen3.5-27b"
                else args.current_root / "build" / artifact_model
            )
            copy_result_tree(build_source, model_root / "build")

            if paper_model == "gemini-3-flash":
                revise_source = args.revise_gemini3_root
                revise_mode = "canonical_plus_infrastructure_recovery"
                copy_result_tree(revise_source, model_root / "revise_code")
            elif paper_model == "claude-opus-4-6":
                revise_source = args.revise_opus_conservative_root
                revise_mode = "two_run_conservative"
                copy_result_tree(revise_source, model_root / "revise_code")
                copy_result_tree(
                    args.current_root / "revise_code" / artifact_model,
                    model_root / "revise_code" / "source_runs" / "historical_current",
                )
                copy_result_tree(
                    args.revise_opus_second_root,
                    model_root / "revise_code" / "source_runs" / "historical_strict_repeat",
                )
            elif paper_model in CONSERVATIVE_CURRENT:
                revise_source = args.current_root / "revise_code" / artifact_model
                revise_mode = "first_run_and_conditional_repeat_conservative"
                copy_result_tree(revise_source, model_root / "revise_code")
            else:
                revise_source = args.revise_restored_root / artifact_model
                revise_mode = "restored_historical_first_call"
                copy_result_tree(revise_source, model_root / "revise_code")

            explain_source = args.current_root / "explain" / artifact_model
            copy_result_tree(explain_source, model_root / "explain")

            build_rows = result_rows(model_root / "build" / "results.json")
            revise_rows = result_rows(model_root / "revise_code" / "results.json")
            explain_rows = result_rows(model_root / "explain" / "results.json")
            build_score = sum(bool(row.get("passed")) for row in build_rows)
            revise_score = sum(bool(row.get("passed")) for row in revise_rows)
            explain_stored_mean = round(
                sum(float(row.get("total_score", 0.0) or 0.0) for row in explain_rows) / 100,
                2,
            )
            expected_build = int(float(table_row["build_pass_at_1_percent"]))
            expected_revise = int(float(table_row["revise_code_gurobi_pass_at_1_percent"]))
            if build_score != expected_build or revise_score != expected_revise:
                raise ValueError(
                    f"{paper_model}: observed Build/Revise {build_score}/{revise_score}, "
                    f"expected {expected_build}/{expected_revise}"
                )

            provenance = {
                "schema_version": "1.0",
                "paper_model": paper_model,
                "artifact_model": artifact_model,
                "solver": "gurobi",
                "instances_per_task": 100,
                "workspace_join": {
                    "build": "build-{instance_id:03d}",
                    "revise_code": "revise-{instance_id:03d}",
                    "explain": "explain-{instance_id:03d}",
                },
                "revise_code_release_mode": revise_mode,
                "paper_table2": {
                    "build_pass_at_1_percent": table_row["build_pass_at_1_percent"],
                    "revise_code_gurobi_percent": table_row["revise_code_gurobi_pass_at_1_percent"],
                    "explain_rubric_mean": table_row["explain_rubric_mean"],
                },
                "stored_artifact_checks": {
                    "build_passed": build_score,
                    "revise_code_passed_under_release_rule": revise_score,
                    "explain_stored_score_mean": explain_stored_mean,
                },
            }
            write_json(model_root / "provenance.json", provenance)

            archive_path = archives / f"{paper_model}.zip"
            write_zip(model_root, archive_path)
            index_rows.append(
                {
                    "paper_model": paper_model,
                    "artifact_model": artifact_model,
                    "archive": f"models/{archive_path.name}",
                    "archive_bytes": archive_path.stat().st_size,
                    "archive_sha256": sha256(archive_path),
                    "build_rows": 100,
                    "build_passed": build_score,
                    "build_code_files": file_count(model_root / "build", "code", "py"),
                    "revise_code_rows": 100,
                    "revise_code_passed": revise_score,
                    "revise_code_files": max(
                        file_count(model_root / "revise_code", "code", "py"),
                        file_count(
                            model_root
                            / "revise_code"
                            / "source_runs"
                            / "historical_current",
                            "code",
                            "py",
                        ),
                    ),
                    "revise_release_mode": revise_mode,
                    "explain_rows": 100,
                    "explain_answer_files": file_count(
                        model_root / "explain", "answers", "txt"
                    ),
                    "explain_stored_mean": f"{explain_stored_mean:.2f}",
                    "explain_table2_mean": table_row["explain_rubric_mean"],
                }
            )

    index_path = args.output_root / "model_index.csv"
    with index_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(index_rows[0]))
        writer.writeheader()
        writer.writerows(index_rows)
    manifest = {
        "schema_version": "1.0",
        "solver": "gurobi",
        "models": 18,
        "tasks": ["build", "revise_code", "explain"],
        "instances_per_model_task": 100,
        "result_rows": 5400,
        "archives": index_rows,
    }
    write_json(args.output_root / "manifest.json", manifest)
    print(json.dumps({"models": 18, "result_rows": 5400}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
