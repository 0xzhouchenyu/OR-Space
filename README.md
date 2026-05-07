# OR-Space · Supplementary Code


This folder contains the **core scripts** released alongside the paper. It is
self-contained and does **not** include: (i) the LLM-under-test rollout
scripts, (ii) the Gurobi-based ground-truth oracle — those live on the
evaluation server and are not redistributed here.

## Contents

| # | Folder | File | What it does | Paper reference |
|---|--------|------|--------------|-----------------|
| 1 | `01_build/` | `generate_build_workspace.py` | Text-only IndustryOR instance → workspace `{docs, data, src}`. Prompts Claude-Opus to emit a **dual-file solver** (`current_heuristic.py` + `utils.py`) that reads CSVs from `../data/` and prints `OBJECTIVE_VALUE: <…>`. | §3 Build task; Table "T→W" |
| 1 | `01_build/` | `expand_workspace_to_filesystem.py` | Materialises a JSON workspace blueprint into a real `iXXX/{docs,data,src}` directory that an Agent can read/write. | §3 Workspace schema |
| 2 | `02_revise_modeling/` | `generate_revise_modeling_L5.py` + `prompts/regenerate_revise_prompt.md` | **Final** Revise-Modeling pipeline used to forge the 100 released instances. An author call (Claude-Opus) consumes the structured L5 prompt (operation vector + coupling/cascading/implicit-dependency criteria + anti-patterns + L5 templates A/B/C) and emits a single revised workspace `{docs, data, src}`; a second independent re-solve pass verifies the revised GT before the file is accepted. An earlier, cheaper "5-archetype R1–R5" generator was discarded as too easy — it is **not** shipped in this archive. | §3 Revise-M pipeline; §4.4 L5 complexity |
| 2 | `02_revise_modeling/` | `qa_redo_revise_gt.py` / `qa_fix_revise_gt.py` / `qa_fix_revise_backlink.py` | Post-hoc QA: re-derive `revised_ground_truth` from authored docs (cross-checked by a second re-solve), snap GT to a target value when the author's code was wrong, and patch specific missing back-link constraints (CBC/GLPK/HiGHS tri-solver agreement). | §4 dataset QA |

| 3 | `03_revise_business/` | `build_business_revise.py` | Rewrites the mechanical `revised_business_requirement.md` into **authentic business voice**. System prompt **forbids meta-language** (no "add a constraint / modify the objective / introduce a variable / penalise …"), requires motivation-first framing, and preserves every numeric parameter and name. | §4.2 Business Voice (W-rev-b); §4.5 Failure Mode 4 |
| 4 | `04_difficulty_judge/` | `llm_revise_difficulty_judge.py` | LLM-as-judge that reads `(orig, revised, diff)` and emits strict JSON with 6-way **archetype** (A/B/C/D/E/F with hard score caps) and three 0-5 axes: **coupling / cascading / implicit_dependency**, aggregated into a 0-15 composite and a tier label. | §4.3 Difficulty Disentanglement; §4.4 |
| 4 | `04_difficulty_judge/` | `cross_judge_gpt_vs_gemini.py` | Cross-validates the judge by re-running with a second strong model (Gemini) and computing GPT↔Gemini agreement per-axis and per-tier. | §4.3 inter-judge agreement |
| 5 | `05_business_quality_rubric/` | `score_business_5dim_rubric.py` | 5-dimension rubric judge scoring every business-voice instance on **D1 Style / D2 No-Meta-Guidance / D3 Numerical Specificity / D4 Motivation / D5 Inference Difficulty**, each 1-5. Used as quality gate before release. | §4.2 W-rev-b validation; Appendix rubric |
| 6 | `06_static_diff/` | `analyze_revise_static_diff.py` | Pure-Python static Diff between `current_heuristic.py` (orig) and revised code: counts `+var / -var / +constr / -constr / mod_constr / mod_obj`, then maps to complexity tier **L1–L5**. Used as an automatic, LLM-free feature for the regression analysis in §4.4 Complexity Dimension Analysis. | §4.4 operation-level ablation |

## API / environment

All LLM scripts read the key from env:

```bash
export OR_SPACE_API_KEY="sk-..."
```

Models used in the released runs:

| Role | Model |
|------|-------|
| Build solver writer | `claude-opus-4-6` |
| Revise-M generator + verifier (final 100) | `claude-opus-4-7` |

| Business-voice rewriter | `gpt-5.4` |
| Difficulty judge (primary) | `gpt-5.1` |
| Difficulty judge (cross) | `gemini-2.5-pro` |
| Quality rubric judge | `gpt-5.4` |

Anything ground-truth-related (running `current_heuristic.py` under Gurobi,
checking `|obj - GT| / |GT| ≤ 0.01`, Pass@1 / feasibility) is produced on the
evaluation server and is **not** in this archive.

## Reproducibility caveats

* The prompts embed exemplars verbatim (see e.g. `STYLE_EXEMPLAR_*` in
  `build_business_revise.py`). Removing these degrades voice consistency.
* The difficulty judge enforces **archetype score caps** — the caps, not the
  rubric text, are what produce the discriminative tier spread in §4.3.
* The static-diff tier L1–L5 is intentionally simpler than the LLM tier; the
  two are reconciled in §4.4.
