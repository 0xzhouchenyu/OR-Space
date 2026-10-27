from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "score_explain", ROOT / "evaluation_programs/explain/score_explain.py"
)
assert SPEC and SPEC.loader
SCORE_EXPLAIN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCORE_EXPLAIN)


def subgrade(score: int) -> dict:
    return {"score": score, "evidence_quote": "candidate evidence"}


def judgment_for(rubric: dict, full: bool = True) -> dict:
    return {
        "reasoning_items": [
            {"criterion_id": item.get("criterion_id", f"c{i}"),
             **{key: subgrade(maximum if full else 0)
                for key, maximum in SCORE_EXPLAIN.REASONING_LIMITS.items()}}
            for i, item in enumerate(rubric["checklist"], 1)
            if item["checklist_type"] == "llm_boolean_judgment"
        ],
        "grounding": {key: subgrade(3 if full else 0) for key in SCORE_EXPLAIN.GROUNDING_KEYS},
        "answer_quality": {key: subgrade(3 if full else 0) for key in SCORE_EXPLAIN.QUALITY_KEYS},
        "hallucination": {"level": "none", "unsupported_claims": []},
        "notes": "Synthetic unit-test fixture; no judge was called.",
    }


class ExplainScorerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rubric = {
            "instance_id": "OR_explain_001", "workspace_id": "or_space_001_explain",
            "checklist": [
                {"criterion_id": "c1", "checklist_type": "exact_match",
                 "target_entities": [f"entity_{i}" for i in range(10)]},
                {"criterion_id": "c3", "checklist_type": "llm_boolean_judgment"},
                {"criterion_id": "c4", "checklist_type": "llm_boolean_judgment"},
            ],
        }
        self.judgment = judgment_for(self.rubric)
        self.answer = {"answer": " ".join(f"entity_{i}" for i in range(8))}

    def score(self, judgment=None, answer=None):
        return SCORE_EXPLAIN.score_one(self.rubric, answer or self.answer,
                                       judgment if judgment is not None else self.judgment)

    def test_normalized_entity_matching(self) -> None:
        answer = "Use `BIG_M = 19,000`; the route is x1[(‘A’, ‘C’)]."
        for entity in ["BIG_M", "19000", "x1[('A', 'C')]"]:
            self.assertTrue(SCORE_EXPLAIN.entity_hit(answer, entity))
        self.assertFalse(SCORE_EXPLAIN.entity_hit("Food II", "I"))

    def test_coverage_excludes_semantic_items(self) -> None:
        poor = judgment_for(self.rubric, False)
        self.assertEqual(self.score()["coverage"], {"hits": 8, "total": 10})
        self.assertEqual(self.score()["dimensions"]["exact_coverage"], 28)
        self.assertEqual(self.score(poor)["dimensions"]["exact_coverage"], 28)
        self.assertEqual(self.score(poor)["score"], 28)

    def test_item_formula_depth_half_credit_and_mean(self) -> None:
        first, second = self.judgment["reasoning_items"]
        first.update(sub_coverage=subgrade(1), sub_causality=subgrade(0),
                     sub_grounding=subgrade(1), sub_depth=subgrade(1))
        for key in SCORE_EXPLAIN.REASONING_LIMITS:
            second[key] = subgrade(0)
        self.assertEqual(self.score()["dimensions"]["reasoning"], 35 * 0.625 / 2)

    def test_anchored_scaling_and_no_double_quote_deduction(self) -> None:
        for key, grade in zip(SCORE_EXPLAIN.GROUNDING_KEYS, [3, 2, 1, 0]):
            self.judgment["grounding"][key] = subgrade(grade)
        for key in SCORE_EXPLAIN.QUALITY_KEYS:
            self.judgment["answer_quality"][key] = {"score": 2, "evidence_quote": ""}
        result = self.score()
        self.assertEqual(result["dimensions"]["grounding"], 10)
        self.assertAlmostEqual(result["dimensions"]["answer_quality"], 20 / 3)

    def test_discrete_penalties_and_empty_claim_override(self) -> None:
        for level, penalty in SCORE_EXPLAIN.PENALTIES.items():
            with self.subTest(level=level):
                self.judgment["hallucination"] = {
                    "level": level, "unsupported_claims": [] if level == "none" else ["bad claim"]}
                self.assertEqual(self.score()["dimensions"]["hallucination_penalty"], penalty)
        self.judgment["hallucination"] = {"level": "severe", "unsupported_claims": []}
        self.assertEqual(self.score()["hallucination"]["level"], "none")
        self.assertEqual(self.score()["dimensions"]["hallucination_penalty"], 0)

    def test_clipping_to_zero_and_full_score(self) -> None:
        poor = judgment_for(self.rubric, False)
        poor["hallucination"] = {"level": "severe", "unsupported_claims": ["bad claim"]}
        self.assertEqual(self.score(poor, {"answer": ""})["score"], 0)
        self.assertEqual(self.score(answer={"answer": " ".join(f"entity_{i}" for i in range(10))})["score"], 100)

    def test_historical_index_and_stable_ids(self) -> None:
        expected = self.score()["score"]
        for index, item in enumerate(self.judgment["reasoning_items"], 1):
            item.pop("criterion_id")
            item["criterion_index"] = index
        self.assertEqual(self.score()["score"], expected)
        self.judgment["reasoning_items"][0]["criterion_id"] = "wrong"
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            self.score()

    def test_reject_missing_duplicate_unknown_reasoning(self) -> None:
        for mode in ["missing", "duplicate", "unknown"]:
            with self.subTest(mode=mode):
                j = copy.deepcopy(self.judgment)
                if mode == "missing":
                    j["reasoning_items"].pop()
                elif mode == "duplicate":
                    j["reasoning_items"].append(copy.deepcopy(j["reasoning_items"][0]))
                else:
                    j["reasoning_items"][0]["criterion_id"] = "unknown"
                with self.assertRaises(ValueError):
                    self.score(j)

    def test_reject_invalid_grades(self) -> None:
        for value in [True, -1, 1.5, 3, float("nan"), float("inf"), "1"]:
            with self.subTest(value=value):
                j = copy.deepcopy(self.judgment)
                j["reasoning_items"][0]["sub_depth"]["score"] = value
                with self.assertRaises(ValueError):
                    self.score(j)
        for dimension in ["grounding", "answer_quality"]:
            j = copy.deepcopy(self.judgment)
            j[dimension].pop(next(iter(j[dimension])))
            with self.assertRaises(ValueError):
                self.score(j)

    def test_reject_obsolete_schema_and_invalid_penalties(self) -> None:
        with self.assertRaisesRegex(ValueError, "Obsolete"):
            self.score({"llm_boolean_judgments": []})
        for hallucination in [
            {"level": "none", "unsupported_claims": ["bad claim"]},
            {"level": "12", "unsupported_claims": ["bad claim"]},
            {"level": "minor", "unsupported_claims": "bad claim"},
            {"level": "minor", "unsupported_claims": [""]},
        ]:
            j = copy.deepcopy(self.judgment)
            j["hallucination"] = hallucination
            with self.assertRaises(ValueError):
                self.score(j)

    def test_judge_prompt_copies_match(self) -> None:
        self.assertEqual((ROOT / "evaluation/explain_evaluation/judge_prompt.md").read_bytes(),
                         (ROOT / "evaluation_programs/explain/judge_prompt.md").read_bytes())

    def test_cli_and_auditable_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            for name, row in [("rubrics", self.rubric),
                              ("answers", {"instance_id": self.rubric["instance_id"], **self.answer}),
                              ("judgments", {"instance_id": self.rubric["instance_id"], **self.judgment})]:
                (p / f"{name}.jsonl").write_text(json.dumps(row) + "\n")
            subprocess.run([sys.executable, str(ROOT / "evaluation_programs/explain/score_explain.py"),
                            "--rubrics", str(p / "rubrics.jsonl"), "--answers", str(p / "answers.jsonl"),
                            "--judgments", str(p / "judgments.jsonl"), "--output", str(p / "scored.jsonl"),
                            "--summary", str(p / "summary.json")], check=True, capture_output=True)
            result = json.loads((p / "scored.jsonl").read_text())
            self.assertEqual(result["score"], 93)
            self.assertEqual(result["protocol_version"], SCORE_EXPLAIN.PROTOCOL_VERSION)
            self.assertEqual(result["reasoning_items"][0]["sub_depth"]["evidence_quote"], "candidate evidence")

    def test_runner_rejects_obsolete_resume_before_client_import(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "judgments.jsonl").write_text(json.dumps({"instance_id": "old"}) + "\n")
            result = subprocess.run([
                sys.executable, str(ROOT / "evaluation_programs/explain/run_judge.py"),
                "--inputs", str(p / "not-read.jsonl"), "--output", str(p / "judgments.jsonl"),
                "--model", "synthetic-model",
            ], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("different protocol, prompt, or model", result.stderr)


if __name__ == "__main__":
    unittest.main()
