"""
regenerate_16_revise.py

Regenerate L5 revise instances for the 16 problems the user flagged as poorly
designed (ambiguous descriptions and meaningless additions). We:

  1. Load the original problem from IndustryOR_Advanced/IndustryOR_<N>.json
     (its `workspace_blueprint` is the authoritative original workspace).
  2. Load the existing IndustryOR_Revise_100/IndustryOR_<N>_revise_*.json as a
     BAD example we show the LLM and tell it NOT to reproduce.
  3. Load a canonical GOOD example (IndustryOR_1_revise_1.json) as a style
     reference.
  4. Build a prompt using the full regenerate_revise_prompt.md plus the
     original-workspace JSON, and ask Claude to return ONE new revise JSON.
  5. Materialize revised_workspace into a temp dir, run
     src/current_heuristic.py, extract OBJECTIVE_VALUE.
  6. Independent verify pass: ask Claude (different temperature, different
     system prompt) to re-solve the problem from scratch using the new docs/
     data/, with NO access to the revise author's src/. If the two values
     agree and differ from original_ground_truth, accept.
  7. Normalise the schema and overwrite the Revise_100/ file (removing any
     other IndustryOR_<N>_revise_*.json so there is exactly one per problem).

Targets (from user): 9 10 26 27 40 45 46 62 64 65 69 86 88 90 92 93.

Usage:
    python scripts/regenerate_16_revise.py                # all 16
    python scripts/regenerate_16_revise.py --nums 9,10    # subset
"""
import os, sys, json, re, time, shutil, tempfile, subprocess, argparse
from openai import OpenAI

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADV_DIR = os.path.join(ROOT, "IndustryOR_Advanced")
REV_DIR = os.path.join(ROOT, "IndustryOR_Revise_100")
PROMPT_PATH = os.path.join(ROOT, "documents", "regenerate_revise_prompt.md")
GOOD_EXAMPLE_PATH = os.path.join(REV_DIR, "IndustryOR_1_revise_1.json")
PY = "/opt/anaconda3/bin/python3"
LOG_DIR = os.path.join(ROOT, "logs_regen16")
os.makedirs(LOG_DIR, exist_ok=True)

CLIENT = OpenAI(
    api_key=os.environ.get("OR_SPACE_API_KEY", "REDACTED_SET_ENV_VAR"),
    base_url="https://api.modelverse.cn/v1/",
    timeout=180.0,   # hard per-request timeout so a hung call fails fast
    max_retries=1,
)
MODEL = "claude-opus-4-7"

DEFAULT_NUMS = [9, 10, 26, 27, 40, 45, 46, 62, 64, 65, 69, 86, 88, 90, 92, 93]
MAX_ROUNDS = 3
SOLVE_TIMEOUT = 120

# ----------------------------- schema normalize ---------------------------- #
TOP_ORDER = [
    "instance_id", "original_instance_id",
    "revise_type", "revise_type_name", "revise_description",
    "metadata", "original_workspace", "revised_workspace", "evaluation",
]
META_ORDER = ["difficulty", "source_dataset", "problem_type", "diff"]
DIFF_ORDER = ["diff_summary", "counts", "op_count", "distinct_ops",
              "involves_coupling", "cascading_effect",
              "complexity_level", "level_name"]
WS_ORDER = ["docs", "data", "src"]
EVAL_ORDER = ["original_ground_truth", "revised_ground_truth", "tolerance"]


def reorder(d, order):
    if not isinstance(d, dict):
        return d
    out = {}
    for k in order:
        if k in d:
            out[k] = d[k]
    for k in d:
        if k not in out:
            out[k] = d[k]
    return out


def normalize(inst):
    # drop alien top-level keys (e.g. 'run')
    for k in list(inst.keys()):
        if k not in TOP_ORDER:
            del inst[k]
    md = inst.get("metadata") or {}
    for k in list(md.keys()):
        if k not in META_ORDER:
            del md[k]
    df = md.get("diff") or {}
    for k in list(df.keys()):
        if k not in DIFF_ORDER:
            del df[k]
    md["diff"] = reorder(df, DIFF_ORDER)
    inst["metadata"] = reorder(md, META_ORDER)
    for wk in ("original_workspace", "revised_workspace"):
        ws = inst.get(wk) or {}
        for k in list(ws.keys()):
            if k not in WS_ORDER:
                del ws[k]
        inst[wk] = reorder(ws, WS_ORDER)
    ev = inst.get("evaluation") or {}
    for k in list(ev.keys()):
        if k not in EVAL_ORDER:
            del ev[k]
    if "tolerance" not in ev:
        ev["tolerance"] = 0.01
    inst["evaluation"] = reorder(ev, EVAL_ORDER)
    return reorder(inst, TOP_ORDER)


# ----------------------------- helpers ------------------------------------ #
def materialize(rw, base):
    for sub in ("docs", "data", "src"):
        d = os.path.join(base, sub)
        os.makedirs(d, exist_ok=True)
        for name, content in (rw.get(sub) or {}).items():
            if content is None:
                continue
            with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                f.write(content)


def run_script(workspace_dir, timeout=SOLVE_TIMEOUT):
    src = os.path.join(workspace_dir, "src", "current_heuristic.py")
    try:
        r = subprocess.run([PY, src], cwd=workspace_dir,
                           capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"


def extract_obj(stdout):
    """Return (obj, status_word). status_word may be 'Infeasible'/'Unbounded'/None.
    For backward compatibility we still return float when parseable, but if the
    script printed a Status line saying Infeasible/Unbounded/Undefined we treat
    it as failure (return None)."""
    if not stdout:
        return None
    txt = stdout
    bad_status = False
    for line in txt.split("\n"):
        if re.search(r"Status\s*[:=]\s*(Infeasible|Unbounded|Undefined|Not Solved)", line, re.I):
            bad_status = True
            break
    if bad_status:
        return None
    for line in reversed(txt.strip().split("\n")):
        m = re.search(r"OBJECTIVE_VALUE\s*[:=]\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)", line)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
    return None


def values_match(a, b, rel=0.005, abs_=1e-3):
    if a is None or b is None:
        return False
    if abs(a - b) <= abs_:
        return True
    return abs(a - b) <= rel * max(abs(a), abs(b), 1.0)


def _strip_think(text):
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _strip_md_fence(text):
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.DOTALL)
    if m:
        return m.group(1)
    return text


def parse_json_response(text):
    text = _strip_think(text)
    text = _strip_md_fence(text)
    s = text.find("{")
    while s >= 0:
        depth = 0
        i = s
        in_str = False
        esc = False
        while i < len(text):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        blob = text[s:i + 1]
                        try:
                            return json.loads(blob)
                        except Exception:
                            break
            i += 1
        s = text.find("{", s + 1)
    raise ValueError("no parseable json in response")


def call_claude(prompt, temperature=0.3, max_tokens=10000):
    # non-streaming, smaller max_tokens to reduce stuck-streaming probability
    resp = CLIENT.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return resp.choices[0].message.content


# ----------------------------- Advanced loader ----------------------------- #
def load_original_from_advanced(num):
    path = os.path.join(ADV_DIR, f"IndustryOR_{num}.json")
    with open(path, encoding="utf-8-sig") as f:
        j = json.load(f)
    wb = j.get("workspace_blueprint") or {}
    orig_ws = {
        "docs": wb.get("docs") or {},
        "data": wb.get("data") or {},
        "src":  wb.get("src") or {},
    }
    orig_gt = (j.get("evaluation") or {}).get("ground_truth")
    if orig_gt is None:
        # other key names
        ev = j.get("evaluation") or {}
        for k in ("optimal_value", "original_ground_truth", "objective_value"):
            if k in ev:
                orig_gt = ev[k]
                break
    return orig_ws, orig_gt, j.get("metadata") or {}


def load_existing_bad(num):
    for fn in os.listdir(REV_DIR):
        if fn.startswith(f"IndustryOR_{num}_revise_") and fn.endswith(".json"):
            with open(os.path.join(REV_DIR, fn), encoding="utf-8-sig") as f:
                return fn, json.load(f)
    return None, None


# ----------------------------- prompts ------------------------------------ #
with open(PROMPT_PATH, encoding="utf-8") as f:
    PROMPT_MD = f.read()

with open(GOOD_EXAMPLE_PATH, encoding="utf-8-sig") as f:
    GOOD_EXAMPLE = json.load(f)


def build_generate_prompt(num, orig_ws, orig_gt, bad_inst):
    """Ask Claude to produce ONE new L5 revise json for IndustryOR_<num>."""
    good_preview = {
        "instance_id": GOOD_EXAMPLE.get("instance_id"),
        "revise_type": GOOD_EXAMPLE.get("revise_type"),
        "revise_type_name": GOOD_EXAMPLE.get("revise_type_name"),
        "revise_description": GOOD_EXAMPLE.get("revise_description"),
        "metadata": GOOD_EXAMPLE.get("metadata"),
        "evaluation": GOOD_EXAMPLE.get("evaluation"),
    }

    bad_preview = None
    if bad_inst is not None:
        bad_preview = {
            "revise_description": bad_inst.get("revise_description"),
            "metadata": (bad_inst.get("metadata") or {}).get("diff"),
            "revised_docs_sample":
                (bad_inst.get("revised_workspace", {}).get("docs") or {}),
        }

    parts = [
        "You are generating a high-quality L5 revise instance for an OR benchmark paper.",
        "Follow the guideline document below STRICTLY.",
        "",
        "=========== GUIDELINE (regenerate_revise_prompt.md) ===========",
        PROMPT_MD,
        "",
        f"=========== ORIGINAL PROBLEM (IndustryOR_{num}) ===========",
        json.dumps(
            {
                "instance_id": f"IndustryOR_{num}",
                "original_ground_truth": orig_gt,
                "original_workspace": orig_ws,
            },
            ensure_ascii=False, indent=2,
        ),
        "",
        "=========== CANONICAL GOOD EXAMPLE (style & rigor reference) ===========",
        json.dumps(good_preview, ensure_ascii=False, indent=2),
        "",
    ]
    if bad_preview is not None:
        parts += [
            "=========== EXISTING POOR REVISE (DO NOT REPRODUCE; contents below are the anti-pattern you must replace) ===========",
            json.dumps(bad_preview, ensure_ascii=False, indent=2),
            "The above is ambiguous / business-meaningless. Design something different, more rigorous, and with real business motivation.",
            "",
        ]
    parts += [
        f"=========== YOUR TASK ===========",
        f"Produce a SINGLE L5 revise JSON for IndustryOR_{num}, using the schema described in the guideline.",
        "Use this exact top-level shape (canonical order):",
        json.dumps({
            "instance_id": f"IndustryOR_{num}_revise_1",
            "original_instance_id": f"IndustryOR_{num}",
            "revise_type": "R1..R5",
            "revise_type_name": "one of the five names",
            "revise_description": "<=250 chars, starts with business motivation",
            "metadata": {
                "difficulty": "Hard",
                "source_dataset": "IndustryOR",
                "problem_type": "Operations Research",
                "diff": {
                    "diff_summary": "...",
                    "counts": {"+variable": 0, "-variable": 0,
                               "+constraint": 0, "-constraint": 0,
                               "modify_constraint": 0, "modify_objective": 0,
                               "modify_data": 0},
                    "op_count": 0,
                    "distinct_ops": 0,
                    "involves_coupling": True,
                    "cascading_effect": True,
                    "complexity_level": "L5",
                    "level_name": "structural",
                },
            },
            "original_workspace": {"docs": "...copy verbatim from ORIGINAL...",
                                   "data": "...copy verbatim...",
                                   "src": "...copy verbatim..."},
            "revised_workspace": {"docs": "...updated business_requirement.md...",
                                  "data": "...updated CSVs...",
                                  "src": "updated current_heuristic.py (+utils.py)"},
            "evaluation": {
                "original_ground_truth": orig_gt,
                "revised_ground_truth": "<float, MUST differ from original>",
                "tolerance": 0.01,
            },
        }, ensure_ascii=False, indent=2),
        "",
        "HARD RULES:",
        "- `original_workspace` MUST be IDENTICAL to the provided ORIGINAL_WORKSPACE (docs/data/src) — copy verbatim.",
        "- `revised_workspace.src/current_heuristic.py` MUST read CSV files from `../data/` with pandas (not hard-coded) and end with a single line: `print(f\"OBJECTIVE_VALUE: {value}\")`.",
        "- Every new parameter you add MUST be named, given a numeric value in `general_parameters.csv` (or a new data file you include), AND explained with its unit & scope in `business_requirement.md`.",
        "- `revise_description` must name every new parameter, start with business motivation, and be <=250 chars.",
        "- distinct_ops >= 4, OR (involves_coupling AND cascading_effect AND op_count >= 5).",
        "- revised_ground_truth must differ from original_ground_truth (otherwise the revise is empty).",
        "- The script must solve to optimality within 60s on CBC.",
        "- **FEASIBILITY (CRITICAL):** the revised model MUST be feasible. Before finalising, mentally check that capacity/budget/demand parameters allow ALL constraints to hold simultaneously. If you tighten a constraint, also relax another or add slack, so a non-trivial optimum exists. Avoid setting brand-new bounds tighter than what the original optimum already attains.",
        "- **BUSINESS-PLAUSIBLE OBJECTIVE VALUE:** if the original problem maximises profit / revenue / production / inventory, the revised optimum MUST be a NON-NEGATIVE, business-meaningful value (a negative profit revise will be rejected). Calibrate any new costs/penalties so the revised optimum is positive and reasonably close to (but distinct from) the original — typically within ±50% — not a sign-flipped trick.",
        "- For min-cost problems the revised optimum must remain a positive cost; for max problems it must remain non-negative and not pathologically tiny.",
        "- **The script MUST guard against silent infeasibility**: after `prob.solve(...)` it MUST check `pulp.LpStatus[prob.status] == 'Optimal'`; otherwise it must `raise RuntimeError(f'Not optimal: {{pulp.LpStatus[prob.status]}}')` BEFORE printing OBJECTIVE_VALUE. This way an infeasible/unbounded model fails fast instead of leaking a meaningless number.",
        "- **Concretely audit data vs constraints**: for every NEW per-day / per-period / per-resource minimum you add, verify that the relevant raw rows in the CSV (e.g. availability columns, capacity rows) actually allow that minimum to be met. If a tight day has insufficient availability, EITHER lower the minimum OR add slack/auxiliary capacity in the data so the model is feasible.",

        "",
        "Return ONLY the JSON object. No markdown fences, no commentary.",
    ]
    return "\n".join(parts)


def build_verify_prompt(num, revised_docs_data):
    """Independent verification: give the LLM ONLY docs+data (no src) and ask it
    to solve from scratch, as an independent modeler."""
    parts = [
        f"You are independently verifying the optimum of IndustryOR_{num} (REVISED variant).",
        "You will receive ONLY the business requirement document and data CSVs. You must re-derive the model from scratch and solve it to optimality using PuLP/CBC (or scipy if nonlinear).",
        "DO NOT attempt to reproduce or second-guess any previous code — build the model yourself.",
        "",
        "============ docs/ ============",
    ]
    for k, v in (revised_docs_data.get("docs") or {}).items():
        parts.append(f"--- docs/{k} ---")
        parts.append(v or "")
    parts.append("============ data/ ============")
    for k, v in (revised_docs_data.get("data") or {}).items():
        parts.append(f"--- data/{k} ---")
        parts.append((v or "")[:8000])
    parts += [
        "",
        "Return ONLY a JSON object of this shape (no markdown):",
        '{"src": {"current_heuristic.py": "<full runnable python that reads ../docs and ../data and prints OBJECTIVE_VALUE: <value>>"}}',
        "The script MUST use relative paths `../docs` and `../data` and end with exactly: print(f\"OBJECTIVE_VALUE: {obj}\")",
    ]
    return "\n".join(parts)


# ----------------------------- per-instance workflow ---------------------- #
def autofix_src_solve(num, rw, log_fp, max_rounds=MAX_ROUNDS):
    """Take the author-provided revised_workspace (incl. src), try to run it.
    If it fails, ask Claude to fix the script (docs/data held fixed)."""
    cur_src = dict(rw.get("src") or {})
    prev_err = ""
    for rnd in range(1, max_rounds + 1):
        with tempfile.TemporaryDirectory() as td:
            materialize({**rw, "src": cur_src}, td)
            rc, out, err = run_script(td)
            obj = extract_obj(out)
            log_fp.write(f"  [author-src run {rnd}] rc={rc} obj={obj}\n")
            if rc == 0 and obj is not None:
                return obj, cur_src
            prev_err = (err or "")[-1500:]
            log_fp.write(f"    stderr tail: {prev_err[-400:]}\n")
        if rnd == max_rounds:
            break
        # ask Claude to fix
        fix_prompt = "\n".join([
            f"The src/current_heuristic.py for IndustryOR_{num} revised variant failed. Fix it.",
            "docs/data below are authoritative and must be read via ../docs and ../data.",
            "============ docs/ ============",
            *[f"--- docs/{k} ---\n{v or ''}" for k, v in (rw.get('docs') or {}).items()],
            "============ data/ ============",
            *[f"--- data/{k} ---\n{(v or '')[:6000]}" for k, v in (rw.get('data') or {}).items()],
            "============ current src/ ============",
            *[f"--- src/{k} ---\n{(v or '')[:6000]}" for k, v in cur_src.items()],
            "============ error ============",
            prev_err,
            "",
            "Return ONLY: {\"src\": {\"current_heuristic.py\": \"<full file>\", \"utils.py\": \"<optional>\"}}",
        ])
        try:
            raw = call_claude(fix_prompt, temperature=0.2)
            obj = parse_json_response(raw)
            new_src = obj["src"]
            for k, v in new_src.items():
                if v:
                    cur_src[k] = v
        except Exception as e:
            log_fp.write(f"    ! fix attempt failed: {e}\n")
    return None, cur_src


def verify_independent(num, rw, log_fp, orig_gt, max_rounds=MAX_ROUNDS):
    prompt = build_verify_prompt(num, rw)
    prev_err = ""
    for rnd in range(1, max_rounds + 1):
        log_fp.write(f"  [verify run {rnd}]\n")
        try:
            raw = call_claude(prompt if rnd == 1 else prompt + f"\n\nPREVIOUS ATTEMPT FAILED, stderr tail:\n{prev_err[-1500:]}\nPlease fix and try again.",
                              temperature=0.4)
            obj = parse_json_response(raw)
            v_src = obj["src"]
        except Exception as e:
            log_fp.write(f"    ! parse: {e}\n"); continue
        with tempfile.TemporaryDirectory() as td:
            materialize({**rw, "src": v_src}, td)
            rc, out, err = run_script(td)
            val = extract_obj(out)
            log_fp.write(f"    rc={rc} obj={val}\n")
            if rc == 0 and val is not None:
                # feasibility & business plausibility check
                msg = None
                if val < -1e-6:  # negative profit/revenue/inventory not acceptable
                    msg = f"negative objective {val} (must be non-negative for max problems)"
                elif orig_gt is not None and abs(val - orig_gt) < 1e-6:
                    msg = f"revised_gt equals original_gt={orig_gt} (empty revise)"
                # detect infeasible via PuLP status
                if "Infeasible" in out or "No solution" in out:
                    msg = f"model reported Infeasible or No solution"
                if msg:
                    prev_err = f"{msg}\n" + (err or "")[-800:]
                    log_fp.write(f"    ! {msg}\n"); continue
                return val, None
            prev_err = (err or "")[-1500:]
    return None, prev_err


def regen_one(num):
    log_path = os.path.join(LOG_DIR, f"{num}.log")
    log_fp = open(log_path, "w")
    log_fp.write(f"=== regen #{num} ===\n")

    orig_ws, orig_gt, _orig_meta = load_original_from_advanced(num)
    bad_fn, bad_inst = load_existing_bad(num)
    log_fp.write(f"orig_gt={orig_gt}  existing_bad_file={bad_fn}\n")
    if orig_gt is None:
        log_fp.write("  ! NO ORIG GT; will still try but skip diff check.\n")

    last_err_preview = ""
    for attempt in range(1, MAX_ROUNDS + 1):
        log_fp.write(f"\n--- generation attempt {attempt}/{MAX_ROUNDS} ---\n")
        prompt = build_generate_prompt(num, orig_ws, orig_gt, bad_inst)
        if last_err_preview:
            prompt += "\n\n=========== PREVIOUS ATTEMPT ISSUE ===========\n" + last_err_preview
        try:
            raw = call_claude(prompt, temperature=0.35 + 0.1 * (attempt - 1))
        except Exception as e:
            log_fp.write(f"  ! claude error: {e}\n"); time.sleep(5); continue
        try:
            inst = parse_json_response(raw)
        except Exception as e:
            log_fp.write(f"  ! parse: {e}\n"); last_err_preview = f"parse error: {e}"; continue

        # override original_workspace with authoritative copy
        inst["original_workspace"] = orig_ws
        # make sure instance_id is right
        inst["original_instance_id"] = f"IndustryOR_{num}"
        inst["instance_id"] = f"IndustryOR_{num}_revise_1"
        ev = inst.get("evaluation") or {}
        if orig_gt is not None:
            ev["original_ground_truth"] = orig_gt
        ev.setdefault("tolerance", 0.01)
        inst["evaluation"] = ev

        rw = inst.get("revised_workspace") or {}
        if not (rw.get("docs") and rw.get("data") and rw.get("src")):
            last_err_preview = "revised_workspace missing docs/data/src"
            log_fp.write(f"  ! {last_err_preview}\n"); continue

        # 1) run author src
        primary_val, fixed_src = autofix_src_solve(num, rw, log_fp)
        if primary_val is None:
            last_err_preview = "author-provided src could not be made to run"
            log_fp.write(f"  ! primary solve failed\n"); continue
        log_fp.write(f"  primary_val={primary_val}\n")
        rw["src"] = fixed_src

        # 2) must differ from orig
        if orig_gt is not None and values_match(primary_val, orig_gt):
            last_err_preview = f"revised_gt={primary_val} equals original_gt={orig_gt}; revise is empty"
            log_fp.write(f"  ! {last_err_preview}\n"); continue

        # 2b) primary feasibility / business plausibility
        if primary_val < -1e-6:
            last_err_preview = (f"primary_val={primary_val} is NEGATIVE; for a max profit/revenue/inventory problem "
                                "the optimum must be >=0. Recalibrate costs/penalties.")
            log_fp.write(f"  ! {last_err_preview}\n"); continue

        # 3) independent verify
        verify_val, verify_err = verify_independent(num, rw, log_fp, orig_gt)
        log_fp.write(f"  verify_val={verify_val}\n")
        if verify_val is None:
            last_err_preview = ("independent verifier could not reproduce a feasible non-negative value: "
                                + (verify_err or "")[:600])
            log_fp.write(f"  ! verify failed\n"); continue
        if not values_match(primary_val, verify_val):
            last_err_preview = f"primary={primary_val} vs verify={verify_val} disagree — description is ambiguous"
            log_fp.write(f"  ! DISAGREE {last_err_preview}\n"); continue

        # accept
        inst["revised_workspace"] = rw
        inst["evaluation"]["revised_ground_truth"] = float(primary_val)
        inst = normalize(inst)

        # write: overwrite existing file if any, standard name _revise_1
        target_path = os.path.join(REV_DIR, f"IndustryOR_{num}_revise_1.json")
        # remove any other variants
        for fn in os.listdir(REV_DIR):
            if fn.startswith(f"IndustryOR_{num}_revise_") and fn.endswith(".json") and fn != f"IndustryOR_{num}_revise_1.json":
                os.remove(os.path.join(REV_DIR, fn))
                log_fp.write(f"  removed old variant {fn}\n")
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(inst, f, ensure_ascii=False, indent=2)
        log_fp.write(f"  WROTE {target_path}  revised_gt={primary_val}\n")
        log_fp.close()
        return True, primary_val

    log_fp.write("\n!!! gave up after all attempts\n")
    log_fp.close()
    return False, None


# ----------------------------- main --------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nums", default=",".join(str(x) for x in DEFAULT_NUMS))
    args = ap.parse_args()
    nums = [int(x) for x in args.nums.split(",") if x.strip()]

    print(f"regenerating {len(nums)} instances: {nums}")
    results = []
    for n in nums:
        t0 = time.time()
        try:
            ok, val = regen_one(n)
        except Exception as e:
            ok, val = False, f"EXC: {e}"
        dt = time.time() - t0
        status = "OK " if ok else "FAIL"
        print(f"  #{n:>3}  {status}  val={val}  ({dt:.0f}s)")
        results.append((n, ok, val, dt))

    print("\n========== SUMMARY ==========")
    for n, ok, val, dt in results:
        print(f"  #{n:>3}  {'OK ' if ok else 'FAIL'}  val={val}  ({dt:.0f}s)")
    ok_ct = sum(1 for _, ok, _, _ in results if ok)
    print(f"\n  {ok_ct}/{len(results)} succeeded")


if __name__ == "__main__":
    main()
