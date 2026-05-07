#!/usr/bin/env python3
"""
Generate business-narrative versions of all 100 revise instances under
`IndustryOR_Revise_100_business/`.

For each source JSON at `IndustryOR_Revise_100/IndustryOR_<num>_revise_<k>.json`,
we produce `IndustryOR_Revise_100_business/IndustryOR_<num>_revise_<k>.json`,
identical in EVERY field EXCEPT:

    revised_workspace.docs.business_requirement.md

which is rewritten by gpt-5.4 into a plausible, motivation-rich, business-voice
narrative that a real OR researcher / business planner would speak. The new text
MUST preserve full numerical specificity (all parameter names, penalty
coefficients, thresholds, time windows) so that the revised GT / code remain
valid, but must NOT use modeling meta-language (no "add a constraint", "modify
the objective", "introduce a variable", "penalise", etc.).

Inputs per file:
    ORIGINAL build-style business_requirement.md  (style anchor)
    OLD revised business_requirement.md           (meaning anchor)
    revise_description                            (compact change summary)

Outputs:
    IndustryOR_Revise_100_business/IndustryOR_<num>_revise_<k>.json  (100 files)
    logs_build_business/cache.json                                   (rerun-safe)
    logs_build_business/build_business.log                           (per-item log)

Run:
    python scripts/build_business_revise.py                 # all 100, 8 workers
    python scripts/build_business_revise.py --instances 1,4,9,10  --concurrency 4
    python scripts/build_business_revise.py --force         # ignore cache, redo all
"""
from __future__ import annotations
import os, sys, json, time, argparse, re
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI

BASE = "."
SRC_DIR = os.path.join(BASE, "IndustryOR_Revise_100")
DST_DIR = os.path.join(BASE, "IndustryOR_Revise_100_business")
LOG_DIR = os.path.join(BASE, "logs_build_business")
CACHE   = os.path.join(LOG_DIR, "cache.json")
LOGF    = os.path.join(LOG_DIR, "build_business.log")
os.makedirs(DST_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

API_KEY  = os.environ.get("OR_SPACE_API_KEY", "REDACTED_SET_ENV_VAR")
BASE_URL = "https://api.shubiaobiao.cn/v1"
MODEL    = "gpt-5.4"

# ---------- Style reference: the user-approved "revise2" example ----------
STYLE_EXEMPLAR_BUILD = (
    "In network communication services, bandwidth plays an important role. Below is a "
    "description of the problem. The bandwidth communication table between several "
    "communication nodes has been extracted into a CSV file. If two nodes cannot be "
    "directly connected, the corresponding bandwidth is $0$. It is required to establish "
    "a link between node A and node E that must pass through service node C (without "
    "loops). The bandwidth of this link is defined as the minimum bandwidth value on the "
    "link. Please refer to the corresponding CSV files in the data folder for specific "
    "parameter values and propose a reasonable link arrangement to maximize the "
    "bandwidth of this link and find out the maximum bandwidth."
)
STYLE_EXEMPLAR_OLD_REVISE = (
    "In network communication services, routing cost plays an important role. Below is a "
    "description of the problem. The bandwidth communication table between several "
    "communication nodes has been extracted into a CSV file. If two nodes cannot be "
    "directly connected, the corresponding bandwidth is $0$. It is required to establish "
    "a link between node A and node E that must pass through service node C, and the "
    "link cannot contain loops. For each direct connection between two nodes, the "
    "routing cost is determined by the available bandwidth on that connection: the cost "
    "equals $100$ minus the corresponding bandwidth value in the table. Therefore, a "
    "direct connection with higher bandwidth carries lower routing cost, while a direct "
    "connection with bandwidth $0$ represents an unavailable connection and cannot be "
    "used to form the link. The total routing cost of a complete link from node A to "
    "node E is defined as the sum of the routing costs of all direct connections "
    "included along the path. Please refer to the corresponding CSV files in the data "
    "folder for specific parameter values, and determine a reasonable loop-free link "
    "arrangement from node A to node E through service node C that yields the smallest "
    "total routing cost, together with this minimum total cost."
)
STYLE_EXEMPLAR_NEW_REVISE = (
    "Our network operations team is reviewing how we route traffic between key service "
    "nodes in the backbone network. The immediate planning question concerns a single "
    "end-to-end connection that has to be arranged from node A to node E, and for "
    "service architecture reasons it must pass through service node C somewhere along "
    "the way. The available direct connections and their bandwidth levels are listed in "
    "the CSV file in the data folder. Wherever the table shows a bandwidth of 0, those "
    "two nodes should be treated as having no direct link available. The route we "
    "choose should be a simple path, meaning traffic should not loop back through the "
    "same node more than once.\n\n"
    "This request comes from a recent latency-related service commitment for premium "
    "traffic. After a post-incident review of delayed transmissions on narrow backbone "
    "segments, the network engineering group asked us to stop judging a route only by "
    "its weakest segment and instead look at the full burden created across the entire "
    "path. To reflect that operating reality, each direct hop now carries a routing "
    "cost based on the channel's bandwidth: a link's cost is set at 100 minus its "
    "bandwidth. In practical terms, narrower channels are treated as more expensive "
    "because they are more likely to create delay and consume scarce routing "
    "flexibility, while wider channels are less costly to use. The total routing cost "
    "of a complete A-to-E route is therefore the sum of these hop-by-hop costs over "
    "every direct connection included in the path.\n\n"
    "Please use the bandwidth communication table from the CSV file in the data folder "
    "to determine which sequence of nodes should carry the connection from A to E, with "
    "node C included on the route and no loops allowed, so that the overall routing "
    "cost is as low as possible, and report that lowest total cost."
)

SYS_PROMPT = f"""You are an operations-research domain writer. You rewrite
"revised business_requirement.md" documents into authentic business prose — the
voice of a real OR researcher, planner, or business stakeholder describing the
problem to a colleague — while preserving the exact underlying mathematical
meaning so that the same revised ground-truth solution and code remain valid.

OBJECTIVES
----------
Given:
  ORIGINAL  — the build-style business_requirement.md (voice anchor)
  OLD_REVISE — a mechanically-written revised business_requirement.md
               (meaning anchor; shows WHAT changed vs. ORIGINAL)
  CHANGE_HINT — a one-sentence description of the revision

Produce: a new revised business_requirement.md that matches ORIGINAL's voice
but now incorporates the revision captured by OLD_REVISE / CHANGE_HINT.

HARD RULES
----------
1. NO meta-modeling language. Do not write "add a constraint", "modify the
   objective", "introduce a variable", "the model should enforce", "penalise",
   "a new constraint states that", "in addition to the original problem",
   "the formulation must now", "subject to", "decision variable", etc. Write as
   a business stakeholder describing reality, not as an engineer annotating a
   model.
2. Motivation first, rule second. Every new restriction or objective change
   must be introduced through a credible business reason: regulation, customer
   contract / SLA, supplier shift, safety policy, ESG/sustainability
   directive, maintenance window, labor agreement, capacity incident,
   strategic board decision, risk mitigation, market volatility — whatever is
   plausible for the domain. Do NOT fabricate unrelated backstory; the
   motivation must be consistent with the underlying problem.
3. Full numerical specificity. Preserve every concrete number, parameter name
   (for example `contract_nurse_pay`, `max_total_contract_starts`,
   `overtime_wage`, `food_I_production_rate`, `training_capacity`), unit
   (kg/h, yuan/kg, weeks, kWh, %, etc.), threshold, time window, and penalty
   coefficient that appears in OLD_REVISE. Never replace a number with a vague
   phrase ("small", "enough", "limited"). Where OLD_REVISE names a parameter
   key, refer to it by the same key in backticks.
4. Do not mention "R1 / R3 / R5", "revise_type", "ground truth", "original
   problem" as such. Never say the phrase "the original problem". Just
   describe the new business situation end-to-end.
5. Keep CSV / data-folder pointers that exist in ORIGINAL ("Please refer to
   the corresponding CSV files in the data folder ..."); phrase them as a
   natural closing instruction.
6. Preserve the underlying MATH. Every logical constraint or objective change
   expressed in OLD_REVISE must still be inferrable by a careful reader. In
   particular:
     • mutual exclusions, binaries, capacity limits, min/max bounds, time
       windows, scenario structures, precedence, coupling, SLA penalties,
       two-stage / lexicographic priorities — all such elements must be
       preserved in substance and magnitude.
     • If OLD_REVISE uses a named indexed variable / parameter / flag (e.g.
       `produce_I_flag[t]`, `inspection_modes`, `y_M,t`), you may paraphrase
       the business meaning but you MUST still mention the key names so the
       solver can align data and code.
7. Length: 2–5 paragraphs. At most ~5× the length of the ORIGINAL build
   description. Do not pad — avoid empty rhetoric, restatement, or boilerplate.
8. Output language: English, matching ORIGINAL.
9. Output format: Return ONLY the new business_requirement.md text. No JSON,
   no markdown code fences, no headings like "### Revised". Plain prose.

STYLE EXEMPLAR (for calibration; do not copy)
---------------------------------------------
ORIGINAL (build):
{STYLE_EXEMPLAR_BUILD}

OLD_REVISE (mechanical):
{STYLE_EXEMPLAR_OLD_REVISE}

NEW_REVISE (target business voice):
{STYLE_EXEMPLAR_NEW_REVISE}

Notice how the new version leads with a stakeholder motivation ("network
operations team ... post-incident review ... latency-related service
commitment"), avoids every modeling meta-phrase, keeps the exact formula
("100 minus bandwidth"), and closes with a natural CSV pointer.

Now write the NEW revised business_requirement.md for the problem the user
gives you.
"""

USER_TMPL = """[ORIGINAL build-style business_requirement.md]
{original}

[OLD revised business_requirement.md — mechanical, meaning anchor]
{old_revise}

[CHANGE_HINT — compact description of the revision]
{change_hint}

[DOMAIN HINTS you may draw on for motivation] {domain}

Please output ONLY the new business-voice revised business_requirement.md.
"""

# --- forbidden meta-phrases (used for lightweight QC; regenerate once if hit) ---
META_PATTERNS = [
    r"\badd(?:s|ed|ing)?\s+a?\s*(?:new\s+)?constraint\b",
    r"\bmodify(?:ing|\s+the)?\s+(?:the\s+)?objective\b",
    r"\bintroduce\s+a?\s*(?:new\s+)?(?:variable|binary|constraint)\b",
    r"\bthe model (?:should|must) (?:enforce|now)\b",
    r"\bin addition to the original problem\b",
    r"\bthe formulation (?:must|should) now\b",
    r"\bdecision variable\b",
    r"\bsubject to\b",
    r"\bpenali[sz]e\b",
    r"\bconstraint stating that\b",
    r"\ba new constraint\b",
    r"\bthe revised (?:problem|model|formulation)\b",
    r"\brevise_type\b",
    r"\bground[-_ ]truth\b",
]


def _find_src(num: int) -> str | None:
    for fn in os.listdir(SRC_DIR):
        m = re.match(rf"IndustryOR_{num}_revise_(\d+)\.json$", fn)
        if m:
            return os.path.join(SRC_DIR, fn)
    return None


def _dst_path_for(src_path: str) -> str:
    return os.path.join(DST_DIR, os.path.basename(src_path))


def _strip_fences(s: str) -> str:
    s = (s or "").strip()
    if s.startswith("```"):
        lines = s.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    return s


def _violations(text: str) -> list[str]:
    hits = []
    for pat in META_PATTERNS:
        if re.search(pat, text, flags=re.IGNORECASE):
            hits.append(pat)
    return hits


def _domain_hint(original_md: str) -> str:
    """Quick heuristic domain tag to help the model pick a plausible motivation."""
    t = original_md.lower()
    tags = []
    for kw, tag in [
        ("hospital", "hospital staffing / nursing policy / infection control"),
        ("nurse", "nursing labor agreement / patient safety / SLA"),
        ("truck", "fleet routing / logistics / fuel policy / driver hours"),
        ("port", "port logistics / demurrage / shipping SLA"),
        ("warehouse", "warehouse operations / picking SLA / labor agreement"),
        ("factory", "factory / manufacturing / safety / cross-contamination"),
        ("production", "production planning / supplier contract / capacity"),
        ("farm", "agriculture / crop rotation / land policy"),
        ("crop", "agronomic policy / ESG / rotation mandate"),
        ("diet", "nutrition plan / health / weekly budget"),
        ("food", "food production / regulation / safety"),
        ("power", "energy / grid tariff / emission cap / ESG"),
        ("energy", "energy / tariff / carbon quota / ESG"),
        ("electric", "electricity tariff / self-generation quota / grid"),
        ("portfolio", "investment policy / risk limit / compliance"),
        ("bank", "credit risk / regulatory limit / compliance"),
        ("bandwidth", "network operations / latency SLA / backbone review"),
        ("network", "network operations / routing policy / SLA"),
        ("motorcycle", "manufacturing / supplier inspection / QA"),
        ("recruit", "recruiting policy / workforce directive"),
        ("soldier", "military workforce / priority assignment"),
        ("spare part", "reliability engineering / maintenance policy"),
        ("reliability", "reliability engineering / mission profile"),
        ("contract", "contract management / SLA / minimum commitment"),
    ]:
        if kw in t:
            tags.append(tag)
    if not tags:
        tags.append("generic operations planning")
    # dedup, keep first 3
    seen = set(); out = []
    for x in tags:
        if x not in seen:
            seen.add(x); out.append(x)
        if len(out) >= 3:
            break
    return "; ".join(out)


def _call_llm(client: OpenAI, original: str, old_revise: str, change_hint: str,
              domain: str, max_retry: int = 3) -> tuple[str, str]:
    """Returns (new_md, err). new_md='' on failure."""
    user = USER_TMPL.format(original=original, old_revise=old_revise,
                            change_hint=change_hint, domain=domain)
    last_err = ""
    for attempt in range(max_retry):
        try:
            r = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYS_PROMPT},
                    {"role": "user",   "content": user},
                ],
                temperature=0.55,
                max_tokens=2000,
            )
            txt = _strip_fences(r.choices[0].message.content or "")
            if not txt or len(txt) < 200:
                last_err = f"output too short ({len(txt)} chars)"; continue
            viol = _violations(txt)
            if viol:
                # one regeneration attempt is embedded by outer loop
                last_err = f"meta-guidance phrases hit: {viol[:3]}"
                continue
            return txt, ""
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            time.sleep(2 + 3 * attempt)
    return "", last_err


def _build_one(num: int, cache: dict, force: bool) -> dict:
    src_path = _find_src(num)
    if src_path is None:
        return {"num": num, "ok": False, "err": "source json not found"}
    dst_path = _dst_path_for(src_path)
    with open(src_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    original   = data["original_workspace"]["docs"]["business_requirement.md"]
    old_revise = data["revised_workspace"]["docs"]["business_requirement.md"]
    change_hint = data.get("revise_description", "") or ""
    # strip any [Patch ...] tail
    change_hint = re.split(r"\n\s*\[Patch ", change_hint, maxsplit=1)[0].strip()

    key = f"{num}:{os.path.basename(src_path)}"
    cached = cache.get(key)
    if (not force) and cached and cached.get("new_md") \
            and cached.get("old_md_hash") == hash(old_revise) \
            and cached.get("orig_md_hash") == hash(original):
        new_md = cached["new_md"]
        reused = True
    else:
        client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=180)
        domain = _domain_hint(original)
        new_md, err = _call_llm(client, original, old_revise, change_hint, domain)
        if not new_md:
            return {"num": num, "ok": False, "err": err or "llm failed",
                    "file": os.path.basename(src_path)}
        cache[key] = {
            "new_md": new_md,
            "old_md_hash":  hash(old_revise),
            "orig_md_hash": hash(original),
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        reused = False

    # Write output JSON: identical to source EXCEPT business_requirement.md
    out = json.loads(json.dumps(data))  # deep copy
    out["revised_workspace"]["docs"]["business_requirement.md"] = new_md
    with open(dst_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    return {"num": num, "ok": True, "reused": reused,
            "file": os.path.basename(dst_path),
            "len": len(new_md)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--instances", type=str, default="",
                    help="comma list, e.g. 1,4,9  (empty = all 1..100)")
    ap.add_argument("--force", action="store_true",
                    help="ignore cache, regenerate every selected instance")
    args = ap.parse_args()
    try: sys.stdout.reconfigure(line_buffering=True)
    except Exception: pass

    # Determine instance list
    if args.instances.strip():
        nums = sorted({int(x) for x in args.instances.split(",") if x.strip().isdigit()})
    else:
        nums = []
        for fn in os.listdir(SRC_DIR):
            m = re.match(r"IndustryOR_(\d+)_revise_\d+\.json$", fn)
            if m: nums.append(int(m.group(1)))
        nums = sorted(set(nums))
    print(f"Selected {len(nums)} instances. concurrency={args.concurrency} "
          f"force={args.force} model={MODEL}", flush=True)

    # Load cache
    cache = {}
    if os.path.exists(CACHE):
        try: cache = json.load(open(CACHE, "r", encoding="utf-8"))
        except Exception: cache = {}

    logf = open(LOGF, "a", encoding="utf-8")
    logf.write(f"\n===== run @ {time.strftime('%Y-%m-%d %H:%M:%S')}  "
               f"n={len(nums)}  force={args.force} =====\n")

    done = 0; ok = 0; reused = 0
    fails = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futs = {pool.submit(_build_one, n, cache, args.force): n for n in nums}
        for fut in as_completed(futs):
            num = futs[fut]
            try:
                res = fut.result()
            except Exception as e:
                res = {"num": num, "ok": False, "err": f"exc:{e}"}
            done += 1
            if res.get("ok"):
                ok += 1
                if res.get("reused"): reused += 1
                tag = "CACHE" if res.get("reused") else "NEW"
                line = f"[{done}/{len(nums)}] #{num} {tag}  {res['file']}  len={res['len']}"
            else:
                fails.append(res)
                line = f"[{done}/{len(nums)}] #{num} FAIL  {res.get('err','')[:160]}"
            print(line, flush=True); logf.write(line + "\n"); logf.flush()

            # Persist cache periodically
            if done % 5 == 0:
                with open(CACHE, "w", encoding="utf-8") as f:
                    json.dump(cache, f, ensure_ascii=False, indent=2)

    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    logf.close()

    print(f"\nDone. ok={ok}/{len(nums)}  (reused={reused})  fails={len(fails)}")
    if fails:
        print("Failed instances:")
        for r in fails:
            print(f"  #{r['num']}: {r.get('err','')[:200]}")


if __name__ == "__main__":
    main()
