from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "score_explain", ROOT / "evaluation_programs/explain/score_explain.py"
)
assert SPEC and SPEC.loader
SCORE_EXPLAIN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCORE_EXPLAIN)


class ExplainScorerTests(unittest.TestCase):
    def test_normalized_entity_matching(self) -> None:
        answer = "Use `BIG_M = 19,000`; the route is x1[(‘A’, ‘C’)]."
        self.assertTrue(SCORE_EXPLAIN.entity_hit(answer, "BIG_M"))
        self.assertTrue(SCORE_EXPLAIN.entity_hit(answer, "19000"))
        self.assertTrue(SCORE_EXPLAIN.entity_hit(answer, "x1[('A', 'C')]"))
        self.assertFalse(SCORE_EXPLAIN.entity_hit("Food II", "I"))

    def test_five_dimensional_total(self) -> None:
        rubric = {
            "instance_id": "OR_explain_001",
            "workspace_id": "or_space_001_explain",
            "checklist": [
                {"checklist_type": "exact_match", "target_entities": ["BIG_M", "19000"]},
                {"checklist_type": "llm_boolean_judgment", "criterion": "causal chain"},
            ],
        }
        judgment = {
            "llm_boolean_judgments": [{"criterion_id": "c2", "hit": 1, "reason": "present"}],
            "reasoning": {"score": 30, "reason": ""},
            "grounding": {"score": 18, "reason": ""},
            "answer_quality": {"score": 9, "reason": ""},
            "hallucination_penalty": {"score": 2, "reason": ""},
        }
        result = SCORE_EXPLAIN.score_one(
            rubric, {"answer": "BIG_M is 19,000."}, judgment
        )
        self.assertEqual(result["coverage"], {"hits": 3, "total": 3})
        self.assertEqual(result["score"], 90.0)


if __name__ == "__main__":
    unittest.main()
