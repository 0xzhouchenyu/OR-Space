#!/usr/bin/env python3
"""
llm_revise_difficulty.py
========================

Use a strong LLM (gpt-5.1) to read each revise instance and produce a
structured, evidence-based difficulty assessment.

For each file under IndustryOR_Revise_100/, the LLM is given:
    - original .py  (current_heuristic.py, utils.py)
    - revised  .py  (current_heuristic.py, utils.py)
    - original data (CSV content)
    - revised  data (CSV content)
    - revise_description  (compact change summary)
    - business_requirement.md (original and revised)

The LLM returns a JSON with these fields:

REAL COUNTS (expand `LpVariable.dicts`, `for i in range(N):` etc. and count
the *true* number of decision variables and constraints):
    orig_var_count, rev_var_count
    orig_constr_count, rev_constr_count
    added_vars, removed_vars
    added_constrs, removed_constrs, modified_constrs
    objective_modified (bool)
    objective_change_type (str, e.g. "add_term", "flip_direction",
                           "replace", "multi_objective", "weighted_sum")
    data_modified (bool)
    data_change_details (str)
    data_only_change (bool)          # whether ONLY data changed (algebraic structure unchanged)
    problem_class_changed (str)      # e.g. "LP->MIP", "MILP->MINLP", "unchanged"

THREE DIFFICULTY DIMENSIONS (0-5 integer score + textual evidence):
    involves_coupling       # problem-logic complexity (vars entangled)
    cascading_effect        # action-connectedness when editing (edit A forces B,C,D)
    implicit_dependency     # edits look local but affect other components

AGGREGATE:
    composite_difficulty    # sum of the 3 dims (0-15)
    difficulty_tier         # "trivial" | "easy" | "medium" | "hard" | "very_hard" | "extreme"
    rationale               # 2-3 sentence summary

Run:
    python scripts/llm_revise_difficulty.py --pilot
    python scripts/llm_revise_difficulty.py --instances 14,50,99
    python scripts/llm_revise_difficulty.py            # all 100
    python scripts/llm_revise_difficulty.py --force    # ignore cache
"""
from __future__ import annotations
import os, sys, json, time, argparse, re, traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI

BASE    = "."
SRC_DIR = os.path.join(BASE, "IndustryOR_Revise_100")
LOG_DIR = os.path.join(BASE, "logs_llm_difficulty")
CACHE   = os.path.join(LOG_DIR, "cache.json")
LOGF    = os.path.join(LOG_DIR, "difficulty.log")
OUT_CSV = os.path.join(BASE, "revise_difficulty_llm.csv")
OUT_JSONL = os.path.join(LOG_DIR, "difficulty_full.jsonl")
os.makedirs(LOG_DIR, exist_ok=True)

API_KEY  = os.environ.get("OR_SPACE_API_KEY", "REDACTED_SET_ENV_VAR")
BASE_URL = "https://api.shubiaobiao.cn/v1"
MODEL    = "gpt-5.1"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


# -------------------- Prompt --------------------
SYSTEM_PROMPT = """You are a senior operations-research (OR) engineer and a rigorous benchmark evaluator.
Your job is to read an ORIGINAL optimization workspace and its REVISED version, and produce a
strict JSON difficulty assessment. You MUST:

1. Count decision variables and constraints by *expanding* loops / dict comprehensions / `LpVariable.dicts(..., idx_set)` using the data actually loaded from CSVs. Do NOT count declarations as "1" when they instantiate many indexed variables.
2. Report all structural changes separately.
3. Score three difficulty dimensions on 0-5 integers, with concrete evidence (cite variable/constraint names or code snippets).
4. Output VALID JSON only (no prose before or after).

STEP 0 — MANDATORY: classify the revise into ONE of these 6 archetypes, which CAP the scores.
This is a HARD CAP. You MUST pick exactly one archetype, and the three dimension scores
MUST obey the cap below (you may score lower, not higher). The goal is DISCRIMINATIVE
SPREAD, so pick the *narrowest* archetype that still covers the revise.

  A. DATA_ONLY          — only scalar values in CSV changed; no algebra change.
                          CAP: coupling≤0, cascade≤1, implicit≤1   (composite ≤ 2)

  B. LOCAL_TWEAK        — change ONE coefficient / bound / objective weight / single constant;
                          at most 1 line of code and 0 new vars/constraints.
                          CAP: coupling≤1, cascade≤1, implicit≤2   (composite ≤ 4)

  C. ADD_TERM           — add ONE new parameter and ONE new objective-term OR ONE new
                          constraint family that references only EXISTING vars (no new var).
                          CAP: coupling≤2, cascade≤2, implicit≤2   (composite ≤ 6)

  D. ADD_VAR_FAMILY     — add ONE new indexed var family (continuous or binary) with its
                          bound + one or two linking constraints + one objective term.
                          This is the MOST COMMON archetype in OR benchmark revises.
                          CAP: coupling≤3, cascade≤3, implicit≤2   (composite ≤ 8)

  E. STRUCTURAL_REWRITE — introduces a NEW structural layer: indicator/setup binaries with
                          big-M linking, multi-period / multi-stage flow balance,
                          multi-mode split, or routing on top of assignment. Multiple new
                          var families + multiple new constraint families.
                          CAP: coupling≤4, cascade≤4, implicit≤3   (composite ≤ 11)

  F. PROBLEM_CLASS_SHIFT — the revise changes the mathematical problem class: LP→MINLP,
                          single-objective → multi-objective lexicographic/weighted-sum,
                          deterministic → stochastic two-stage, or adds a genuinely new
                          NP-hard layer (VRP with time windows, scheduling with sequence-
                          dependent setup, bilevel, column-generation pattern).
                          CAP: coupling≤5, cascade≤5, implicit≤5   (composite ≤ 15)

CRITICAL: Only ~5-10% of revises are archetype F. About 15-20% are E. Most (~50-60%) are
D. DO NOT inflate to E/F unless the revise clearly meets the STRUCTURAL criteria above.
DO NOT deflate genuine F revises to E just to be safe.

After choosing the archetype, score the three dimensions HONESTLY WITHIN THE CAP.
You MUST include the archetype in the output JSON as field "archetype" (one of A/B/C/D/E/F).

Per-dimension anchors (keep within archetype cap):

[involves_coupling]  --  Problem-logic complexity: entanglement between decision variables.
  0 = no coupling change (only scalar value changed; algebra identical).
  1 = minimal — one new var OR one new constraint family, interacting with at most ONE existing family.
  2 = moderate — a new indexed var family that plugs into 2-3 existing constraint families through
       simple aggregation (sum) or simple upper/lower bound links. No new logical linking.
  3 = substantial — a logical-OR / indicator / assignment-packing structure is introduced (e.g., "if
       binary y=1 then continuous x ≤ M"), OR a shared capacity couples several previously
       independent variable blocks.
  4 = strong — genuine MULTI-STAGE coupling: flow balance across stages, inventory carry-over,
       routing with time windows, or a joint index (i,j,t) appearing in ≥3 constraint families
       AND the new structure is not a straightforward bound.
       Anti-pattern: do NOT give 4 just because "many constraints touch the new var" if they are
       all simple capacity/aggregation links — that is 2 or 3.
  5 = extreme — multi-dimensional joint index with non-linear or quadratic coupling, bilevel
       structure, column-generation-style pattern, or the revise introduces a structurally new
       problem class (e.g., VRP on top of a previous assignment model).

[cascading_effect]  --  Action-connectedness: edit A FORCES consistent edits in B, C, D across the codebase.
  0 = no cascade (algebra unchanged; at most a constant changes).
  1 = minimal — ≤2 logical edit sites (e.g., one new LpVariable + one new constraint line).
  2 = moderate — 3-4 logical edit sites: usually "one new var family + its bound + one constraint
       family + one objective term". This is the MOST COMMON case for benchmark revises.
  3 = substantial — 5-7 logical edit sites: multiple constraint families must be updated
       consistently, data loading + param mapping touched, output/report block updated.
  4 = strong — 8-12 edit sites; index-set changes propagate through the entire model; CSV schema
       also changes and several loaders must be rewritten.
       Anti-pattern: do NOT give 4 just because the code is long — count only LOGICALLY distinct
       edit sites (a 20-line for-loop rewrite is usually 1 site).
  5 = extreme — near-complete rewrite; >12 logical edit sites; almost every block must change.

[implicit_dependency]  --  Edits LOOK local but SILENTLY affect correctness elsewhere (traps).
  0 = none — edits are clearly local; a first-principles reader sees every effect.
  1 = minimal — a single RHS change makes one other constraint marginally tighter/looser; still
       obvious on inspection.
  2 = moderate — a parameter or coefficient change renders one existing constraint redundant,
       OR the feasible region shape changes in a way that a novice might miss.
  3 = substantial — a structural edit silently changes which variables are integer-feasible, or
       Big-M must be retightened to keep the MIP LP-relaxation useful; a careful reviewer needs
       to re-derive bounds.
       Anti-pattern: do NOT give 3 just because "multiple constraints are edited". This axis is
       specifically about NON-OBVIOUS side effects, not about edit volume.
  4 = strong — a seemingly local edit removes/introduces feasibility in a non-obvious way, or
       requires re-deriving dual/Big-M constants from scratch. The trap is genuine — an engineer
       who edits only the "obvious" site would ship a wrong model.
  5 = extreme — global reasoning required: e.g., changing one objective weight silently makes a
       whole family of constraints vacuous, or unit/dimension mismatch introduced by the revise.

CRITICAL: These three axes should be LARGELY INDEPENDENT. A pure "add one constraint family"
revise is typically (coupling=2, cascade=2, implicit=0 or 1), giving composite 4-5 = medium.
Do NOT let a single "this looks like a big revise" vibe push all three scores up together.

Calibration examples (use these as reference points):
  * "Change a single capacity from 100 to 150 in CSV" → coupling=0, cascade=0, implicit=0  (trivial)
  * "Add a new product type with its own demand row, requiring one new constraint per period" →
       coupling=1, cascade=2, implicit=0  (composite=3, easy)
  * "Add a setup/fixed-cost binary y_j with linking constraint x_j ≤ M·y_j and a cost term in objective" →
       coupling=3, cascade=2, implicit=1  (composite=6, medium)
  * "Replace single-period model with 4-period inventory carry-over (new flow balance, time-indexed
       vars, multi-period demand)" → coupling=4, cascade=3, implicit=2  (composite=9, hard)
  * "Add a routing/VRP layer on top of an assignment model with time windows" →
       coupling=5, cascade=4, implicit=2-3  (composite=11-12, very_hard)
  * "Multi-objective Pareto reformulation with epsilon-constraint scheme + multi-scenario stochastic
       layer + non-obvious coupling between scenarios" → 5+5+4 = extreme

Counting rules:
  * `x = LpVariable.dicts("x", range(T))` with T=10 counts as 10 decision variables.
  * `for t in range(T): prob += x[t] <= cap[t]` counts as T constraints.
  * Treat objective as 1 "objective expression", not a constraint.
  * For data diff: a changed *value* of one scalar parameter is NOT a structural change.
    A new column, a new row family, or a new CSV file IS structural.

Output SCHEMA (STRICT JSON, no markdown):
{
  "archetype": "A" | "B" | "C" | "D" | "E" | "F",
  "archetype_justification": "one sentence citing concrete structural evidence",
  "orig_var_count": int,
  "rev_var_count": int,
  "orig_constr_count": int,
  "rev_constr_count": int,
  "added_vars": int,
  "removed_vars": int,
  "added_constrs": int,
  "removed_constrs": int,
  "modified_constrs": int,
  "objective_modified": bool,
  "objective_change_type": "unchanged" | "add_term" | "remove_term" | "flip_direction" | "replace" | "multi_objective" | "weighted_sum" | "other",
  "data_modified": bool,
  "data_change_details": "short natural-language description; empty if none",
  "data_only_change": bool,
  "problem_class_changed": "unchanged" | "LP->MIP" | "LP->MILP" | "MILP->MINLP" | "LP->QP" | "added_binary" | "other",
  "involves_coupling": {"score": 0-5, "evidence": "..."},
  "cascading_effect":  {"score": 0-5, "evidence": "..."},
  "implicit_dependency":{"score": 0-5, "evidence": "..."},
  "composite_difficulty": int,          // will be recomputed by us as coupling+cascade+implicit; you still output it but we recompute
  "difficulty_tier": "trivial" | "easy" | "medium" | "hard" | "very_hard" | "extreme",
  "rationale": "2-3 sentence summary"
}

Tier calibration (TARGET DISTRIBUTION over ~100 benchmark revises, STRICT):
We EXPECT approximately: trivial ~5%, easy ~20%, medium ~40%, hard ~25%, very_hard ~8%, extreme ~2%.
If you find yourself emitting very_hard/extreme more than 10% of the time, you are scoring too high.

  trivial    (sum 0-1):  only scalar-value data change; code needs ≤5 char edit.
  easy       (sum 2-4):  single local edit — one new constraint family OR one new parameter +
                          its objective term. Clear, self-contained.
  medium     (sum 5-8):  DEFAULT bucket for "add one var family + a few constraints + objective
                          update + maybe a bound tweak". Most realistic benchmark revises land here.
  hard       (sum 9-11): multi-family edits; big-M / indicator-binary linking; 2 of the 3
                          dimensions hit 3-4. A careful engineer still finishes in <30 min.
  very_hard  (sum 12-13): genuine structural rewrite — at least TWO dimensions at 4 or one at 5;
                          multi-stage coupling AND cascade across many sites AND some non-obvious
                          trap. Reserve this bucket for the upper ~8% of the benchmark.
  extreme    (sum 14-15): near-complete redesign — must satisfy AT LEAST ONE of:
                            (a) problem class fundamentally changed (new NP-hard combinatorial
                                layer on top of the previous model),
                            (b) multi-objective / stochastic / bilevel reformulation,
                            (c) at least one dimension scored 5 + strong traps (implicit ≥3).
                          Top ~2% only.

Be CRITICAL. The PRIOR is that a benchmark revise is MEDIUM. Push DOWN toward medium unless you
have concrete, cite-able evidence for hard/very_hard. Do NOT use very_hard/extreme as a lazy bucket
for "this revise looks non-trivial". Require SPECIFIC structural evidence.
"""


def trim_csv(csv_text: str, max_rows: int = 40) -> str:
    """Keep CSV compact: header + first N rows if huge."""
    if not csv_text:
        return ""
    lines = csv_text.splitlines()
    if len(lines) <= max_rows + 2:
        return csv_text
    return "\n".join(lines[:max_rows] + [f"... ({len(lines)-max_rows} more rows truncated)"])


def build_user_prompt(instance: dict) -> str:
    ows = instance.get("original_workspace", {})
    rws = instance.get("revised_workspace", {})

    o_docs = ows.get("docs", {}).get("business_requirement.md", "") or ""
    r_docs = rws.get("docs", {}).get("business_requirement.md", "") or ""

    o_src = ows.get("src", {})
    r_src = rws.get("src", {})

    o_data = ows.get("data", {})
    r_data = rws.get("data", {})

    # list data file keys, show trimmed contents
    def fmt_csv_block(fdict):
        if not fdict:
            return "(no data files)"
        out = []
        for k, v in fdict.items():
            if isinstance(v, str):
                out.append(f"--- {k} ---\n{trim_csv(v)}")
            else:
                out.append(f"--- {k} ---\n{json.dumps(v, ensure_ascii=False, indent=2)[:1500]}")
        return "\n\n".join(out)

    def fmt_src_block(fdict):
        if not fdict:
            return "(no src files)"
        parts = []
        for k, v in fdict.items():
            if not isinstance(v, str):
                v = json.dumps(v, ensure_ascii=False)
            parts.append(f"--- {k} ---\n{v}")
        return "\n\n".join(parts)

    parts = [
        f"# instance_id: {instance.get('instance_id','?')}",
        f"# revise_type: {instance.get('revise_type','?')} - {instance.get('revise_type_name','?')}",
        "",
        "## revise_description",
        (instance.get("revise_description") or "")[:2000],
        "",
        "## ORIGINAL business_requirement.md",
        o_docs[:3000],
        "",
        "## REVISED business_requirement.md",
        r_docs[:3000],
        "",
        "## ORIGINAL src/ (Python code, read carefully to count real variables and constraints)",
        fmt_src_block(o_src),
        "",
        "## REVISED  src/ (Python code, read carefully to count real variables and constraints)",
        fmt_src_block(r_src),
        "",
        "## ORIGINAL data/ (parameters used to expand var/constr indices)",
        fmt_csv_block(o_data),
        "",
        "## REVISED  data/",
        fmt_csv_block(r_data),
        "",
        "Now emit the STRICT JSON difficulty assessment described in the system instructions.",
    ]
    return "\n".join(parts)


# -------------------- LLM call --------------------
def call_llm(messages, max_retries=3):
    last_err = None
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                response_format={"type": "json_object"},
                timeout=300,
            )
            return resp.choices[0].message.content
        except Exception as e:
            last_err = e
            time.sleep(3 + 5 * attempt)
    raise RuntimeError(f"LLM call failed after {max_retries} retries: {last_err}")


def score_one(fname: str) -> dict:
    fpath = os.path.join(SRC_DIR, fname)
    with open(fpath) as f:
        instance = json.load(f)
    user = build_user_prompt(instance)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
    raw = call_llm(messages) or ""
    if not isinstance(raw, str):
        raw = str(raw)
    try:
        data = json.loads(raw)
    except Exception:
        # try to extract JSON block
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            raise ValueError(f"cannot parse JSON from model, first 300 chars: {raw[:300]}")
        data = json.loads(m.group(0))

    # ---- enforce composite = coupling + cascading + implicit (0-15) ----
    def _s(key):
        try:
            return int((data.get(key) or {}).get("score", 0))
        except Exception:
            return 0
    c1 = _s("involves_coupling")
    c2 = _s("cascading_effect")
    c3 = _s("implicit_dependency")
    comp = c1 + c2 + c3
    data["composite_difficulty"] = comp

    # ---- enforce tier from comp (5-tier; aligned with archetype caps: C≤6, D≤8, E≤11, F≤15) ----
    def comp2tier(x):
        if x <= 2:  return "trivial"
        if x <= 5:  return "easy"
        if x <= 8:  return "medium"
        if x <= 11: return "hard"
        return "very_hard"   # 12-15
    data["difficulty_tier"] = comp2tier(comp)
    return data


# -------------------- IO helpers --------------------
def parse_build_id(fname: str) -> int:
    m = re.match(r"IndustryOR_(\d+)_revise(?:_\d+)?\.json$", fname)
    return int(m.group(1)) if m else -1


def load_cache():
    if os.path.exists(CACHE):
        try:
            return json.load(open(CACHE))
        except Exception:
            return {}
    return {}


def save_cache(cache):
    tmp = CACHE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CACHE)


def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOGF, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


# -------------------- Main pipeline --------------------
def run(files, concurrency, force):
    cache = {} if force else load_cache()
    todo = [f for f in files if f not in cache]
    log(f"total={len(files)}, cached={len(files)-len(todo)}, to_run={len(todo)}, concurrency={concurrency}")

    def worker(fname):
        t0 = time.time()
        try:
            result = score_one(fname)
            log(f"OK  {fname}  tier={result.get('difficulty_tier')}  comp={result.get('composite_difficulty')}  ({time.time()-t0:.1f}s)")
            return fname, result, None
        except Exception as e:
            tb = traceback.format_exc(limit=2)
            log(f"ERR {fname}: {e}")
            return fname, None, f"{e}\n{tb}"

    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futs = {ex.submit(worker, f): f for f in todo}
        done_count = 0
        for fut in as_completed(futs):
            fname, result, err = fut.result()
            done_count += 1
            if result is not None:
                cache[fname] = result
                # periodic save
                if done_count % 5 == 0:
                    save_cache(cache)
    save_cache(cache)

    return cache


def write_outputs(cache, files):
    import csv as _csv
    fieldnames = [
        "build_id", "file",
        "archetype", "archetype_justification",
        "orig_var_count", "rev_var_count",
        "orig_constr_count", "rev_constr_count",
        "added_vars", "removed_vars",
        "added_constrs", "removed_constrs", "modified_constrs",
        "objective_modified", "objective_change_type",
        "data_modified", "data_only_change", "data_change_details",
        "problem_class_changed",
        "coupling_score", "coupling_evidence",
        "cascading_score", "cascading_evidence",
        "implicit_score", "implicit_evidence",
        "composite_difficulty", "difficulty_tier",
        "rationale",
    ]
    out_rows = []
    for fname in files:
        d = cache.get(fname)
        if not d:
            continue
        def dim(k):
            x = d.get(k, {}) or {}
            return x.get("score"), x.get("evidence", "")
        cs, ce = dim("involves_coupling")
        ks, kv = dim("cascading_effect")
        isc, iev = dim("implicit_dependency")
        out_rows.append({
            "build_id": parse_build_id(fname),
            "file": fname,
            "archetype": d.get("archetype"),
            "archetype_justification": d.get("archetype_justification"),
            "orig_var_count":   d.get("orig_var_count"),
            "rev_var_count":    d.get("rev_var_count"),
            "orig_constr_count":d.get("orig_constr_count"),
            "rev_constr_count": d.get("rev_constr_count"),
            "added_vars":       d.get("added_vars"),
            "removed_vars":     d.get("removed_vars"),
            "added_constrs":    d.get("added_constrs"),
            "removed_constrs":  d.get("removed_constrs"),
            "modified_constrs": d.get("modified_constrs"),
            "objective_modified":     d.get("objective_modified"),
            "objective_change_type":  d.get("objective_change_type"),
            "data_modified":          d.get("data_modified"),
            "data_only_change":       d.get("data_only_change"),
            "data_change_details":    d.get("data_change_details"),
            "problem_class_changed":  d.get("problem_class_changed"),
            "coupling_score":     cs,
            "coupling_evidence":  ce,
            "cascading_score":    ks,
            "cascading_evidence": kv,
            "implicit_score":     isc,
            "implicit_evidence":  iev,
            "composite_difficulty": d.get("composite_difficulty"),
            "difficulty_tier":      d.get("difficulty_tier"),
            "rationale":            d.get("rationale"),
        })
    out_rows.sort(key=lambda r: r["build_id"])
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = _csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)
    with open(OUT_JSONL, "w", encoding="utf-8") as f:
        for fname in files:
            d = cache.get(fname)
            if d:
                f.write(json.dumps({"file": fname, **d}, ensure_ascii=False) + "\n")
    log(f"Wrote {OUT_CSV} ({len(out_rows)} rows)")
    log(f"Wrote {OUT_JSONL}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instances", type=str, default="",
                    help="comma-separated build_ids to evaluate, e.g. '14,50,99'")
    ap.add_argument("--pilot", action="store_true",
                    help="shortcut for --instances 14,50,99 (hard/medium/easy sample)")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--force", action="store_true", help="ignore cache")
    args = ap.parse_args()

    all_files = sorted(f for f in os.listdir(SRC_DIR) if f.endswith(".json"))
    if args.pilot:
        target_ids = {14, 50, 99}
    elif args.instances:
        target_ids = {int(x) for x in args.instances.split(",") if x.strip()}
    else:
        target_ids = None

    if target_ids is not None:
        files = [f for f in all_files if parse_build_id(f) in target_ids]
    else:
        files = all_files

    log(f"selected {len(files)} files to evaluate")
    cache = run(files, args.concurrency, args.force)
    write_outputs(cache, files)

    # --- summary ---
    tiers = {}
    for f in files:
        d = cache.get(f, {})
        t = d.get("difficulty_tier", "?")
        tiers[t] = tiers.get(t, 0) + 1
    log(f"TIER DISTRIBUTION: {tiers}")


if __name__ == "__main__":
    main()
