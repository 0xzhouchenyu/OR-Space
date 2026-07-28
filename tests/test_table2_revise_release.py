from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "validate_table2_revise_release.py"
SPEC = importlib.util.spec_from_file_location("validate_table2_revise_release", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

MATERIALIZER_PATH = ROOT / "tools" / "materialize_revise_per_instance.py"
MATERIALIZER_SPEC = importlib.util.spec_from_file_location(
    "materialize_revise_per_instance",
    MATERIALIZER_PATH,
)
assert MATERIALIZER_SPEC is not None and MATERIALIZER_SPEC.loader is not None
MATERIALIZER = importlib.util.module_from_spec(MATERIALIZER_SPEC)
MATERIALIZER_SPEC.loader.exec_module(MATERIALIZER)


class Table2ReviseReleaseTest(unittest.TestCase):
    def test_provisional_structure_is_valid(self) -> None:
        errors = MODULE.validate(
            ROOT / "results" / "gurobi" / "revise_code",
            allow_provisional=True,
        )
        self.assertEqual(errors, [])

    def test_archival_gate_fails_closed(self) -> None:
        errors = MODULE.validate(
            ROOT / "results" / "gurobi" / "revise_code",
            allow_provisional=False,
        )
        self.assertTrue(any("archival gate failed" in error for error in errors))

    def test_pass_both_at_2_uses_intersection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            model = "artifact-model"
            first_model = root / "attempt_1" / model
            second_model = root / "attempt_2" / model
            first_model.mkdir(parents=True)
            second_model.mkdir(parents=True)
            (first_model / "results.json").write_text(
                json.dumps(
                    [
                        {"id": 1, "status": "Success", "passed": True},
                        {"id": 2, "status": "WrongValue", "passed": False},
                        {"id": 3, "status": "Success", "passed": True},
                    ]
                ),
                encoding="utf-8",
            )
            (second_model / "results.json").write_text(
                json.dumps(
                    [
                        {"id": 1, "status": "WrongValue", "passed": False},
                        {"id": 2, "status": "Success", "passed": True},
                        {"id": 3, "status": "Success", "passed": True},
                    ]
                ),
                encoding="utf-8",
            )
            catalog = [
                {
                    "instance_id": value,
                    "benchmark_instance_id": f"IndustryOR_{value}",
                    "workspace_sha256": f"hash-{value}",
                }
                for value in (1, 2, 3)
            ]
            rows = MATERIALIZER.materialize_rows(
                [{"paper_model": "paper-model", "artifact_model": model}],
                catalog,
                attempt_1_root=root / "attempt_1",
                attempt_2_root=root / "attempt_2",
                attempt_2_policy="all_instances",
            )
            self.assertEqual(
                [row["pass_both_at_2"] for row in rows],
                ["false", "false", "true"],
            )

    def test_first_passes_only_is_valid_for_pass_both(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            model = "artifact-model"
            for attempt in ("attempt_1", "attempt_2"):
                (root / attempt / model).mkdir(parents=True)
            (root / "attempt_1" / model / "results.json").write_text(
                json.dumps(
                    [
                        {"id": 1, "status": "Success", "passed": True},
                        {"id": 2, "status": "WrongValue", "passed": False},
                    ]
                ),
                encoding="utf-8",
            )
            (root / "attempt_2" / model / "results.json").write_text(
                json.dumps(
                    [{"id": 1, "status": "Success", "passed": True}]
                ),
                encoding="utf-8",
            )
            catalog = [
                {
                    "instance_id": value,
                    "benchmark_instance_id": f"IndustryOR_{value}",
                    "workspace_sha256": f"hash-{value}",
                }
                for value in (1, 2)
            ]
            rows = MATERIALIZER.materialize_rows(
                [{"paper_model": "paper-model", "artifact_model": model}],
                catalog,
                attempt_1_root=root / "attempt_1",
                attempt_2_root=root / "attempt_2",
                attempt_2_policy="first_passes_only",
            )
            self.assertEqual(
                [row["pass_both_at_2"] for row in rows],
                ["true", "false"],
            )


if __name__ == "__main__":
    unittest.main()
