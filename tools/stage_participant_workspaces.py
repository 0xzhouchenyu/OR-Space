#!/usr/bin/env python3
"""Create participant-visible OR-Space workspaces from the authoring archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Iterable


TASK_DIRS = {
    "build": "build_workspaces",
    "revise": "revise_workspaces",
    "explain": "explain_workspaces",
}
REVISE_CODE_FILES = {
    "current_heuristic.py",
    "utils.py",
    "gurobi_pulp_compat.py",
    "gurobi_execution_record.py",
}
SENSITIVE_TERMS = {
    "answer", "expected", "ground_truth", "objective", "oracle", "reference",
    "rubric", "score", "solution", "target",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sensitive_key(key: str) -> bool:
    normalized = key.casefold().replace("-", "_")
    return any(term in normalized for term in SENSITIVE_TERMS)


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: sanitize(item) for key, item in value.items() if not sensitive_key(str(key))}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    return value


def files_below(root: Path) -> Iterable[Path]:
    if not root.exists():
        return
    for path in sorted(root.rglob("*")):
        if path.is_file():
            yield path


class Stager:
    def __init__(self, source: Path, output: Path, source_id: str) -> None:
        self.source = source
        self.output = output
        self.source_id = source_id
        self.records: list[dict[str, Any]] = []
        self.counts = {task: 0 for task in TASK_DIRS}

    def copy(self, task: str, workspace: str, source: Path, destination: Path) -> None:
        if source.is_symlink():
            raise ValueError(f"Symlinks are not permitted: {source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.name == "metadata.json":
            payload = sanitize(json.loads(source.read_text(encoding="utf-8")))
            destination.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        else:
            shutil.copyfile(source, destination)
        self.records.append(
            {
                "task": task,
                "workspace": workspace,
                "path": str(destination.relative_to(self.output)),
                "bytes": destination.stat().st_size,
                "sha256": sha256(destination),
            }
        )

    def copy_tree(self, task: str, workspace: str, source: Path, destination: Path) -> None:
        for path in files_below(source):
            self.copy(task, workspace, path, destination / path.relative_to(source))

    def empty_src(self, task: str, workspace: str, destination: Path) -> None:
        marker = destination / ".gitkeep"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("", encoding="utf-8")
        self.records.append(
            {
                "task": task,
                "workspace": workspace,
                "path": str(marker.relative_to(self.output)),
                "bytes": 0,
                "sha256": sha256(marker),
            }
        )

    def stage_build(self, instance: Path, destination: Path) -> None:
        for name in ("docs", "data"):
            self.copy_tree("build", instance.name, instance / name, destination / name)
        self.copy("build", instance.name, instance / "metadata.json", destination / "metadata.json")
        self.empty_src("build", instance.name, destination / "src")

    def stage_revise(self, instance: Path, destination: Path) -> None:
        for version in ("original", "revised"):
            for name in ("docs", "data"):
                self.copy_tree(
                    "revise", instance.name, instance / version / name, destination / version / name
                )
        original_src = instance / "original" / "src"
        for name in sorted(REVISE_CODE_FILES):
            source = original_src / name
            if source.is_file():
                self.copy("revise", instance.name, source, destination / "original" / "src" / name)
        self.copy("revise", instance.name, instance / "metadata.json", destination / "metadata.json")
        self.empty_src("revise", instance.name, destination / "revised" / "src")

    def stage_explain(self, instance: Path, destination: Path) -> None:
        for version in ("original", "revised"):
            self.copy_tree("explain", instance.name, instance / version, destination / version)
        self.copy("explain", instance.name, instance / "metadata.json", destination / "metadata.json")

    def run(self) -> None:
        if self.output.exists():
            raise FileExistsError(f"Output already exists: {self.output}")
        self.output.mkdir(parents=True)
        for task, directory in TASK_DIRS.items():
            instances = sorted(
                (path for path in (self.source / directory).glob("instance_*") if path.is_dir()),
                key=lambda path: int(path.name.split("_")[-1]),
            )
            if len(instances) != 100:
                raise ValueError(f"Expected 100 {task} instances, found {len(instances)}")
            for instance in instances:
                getattr(self, f"stage_{task}")(
                    instance, self.output / directory / instance.name
                )
                self.counts[task] += 1
        metadata = self.output / "release_metadata"
        metadata.mkdir()
        manifest = {
            "schema_version": "1.0",
            "source_snapshot_id": self.source_id,
            "revise_view": "revise-code",
            "workspace_counts": self.counts,
            "visibility": {
                "build": "documents, data, sanitized task metadata, empty src",
                "revise": "original/revised documents and data, correct original heuristic and utility/runtime code, empty revised src",
                "explain": "validated original/revised documents, data, reference code, logs, solver records, and sanitized question metadata",
            },
            "files": sorted(self.records, key=lambda row: row["path"]),
        }
        (metadata / "staging_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


def find_root(source: Path) -> Path:
    candidates = [source, *[path for path in source.iterdir() if path.is_dir()]]
    for candidate in candidates:
        if all((candidate / directory).is_dir() for directory in TASK_DIRS.values()):
            return candidate
    raise FileNotFoundError("Could not locate build_workspaces, revise_workspaces, explain_workspaces")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-id", required=True)
    args = parser.parse_args()
    Stager(find_root(args.source.resolve()), args.output.resolve(), args.source_id).run()
    print(f"Staged participant workspaces at {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

