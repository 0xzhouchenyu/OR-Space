from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "validate_table2_revise_release.py"
SPEC = importlib.util.spec_from_file_location("validate_table2_revise_release", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


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


if __name__ == "__main__":
    unittest.main()
