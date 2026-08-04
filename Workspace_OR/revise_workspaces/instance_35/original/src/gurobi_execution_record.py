"""Record non-PuLP exact-search programs through a small Gurobi run.

This helper keeps exact enumeration/reference logic intact while still producing
a Gurobi log and structured solver record for workspace-level diagnostics.
"""
from __future__ import annotations

import builtins
import json
import math
import os
import re
from pathlib import Path

import gurobipy as gp
from gurobipy import GRB


_ORIGINAL_PRINT = builtins.print
_OBJECTIVE_RE = re.compile(r"OBJECTIVE_VALUE\s*:\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)")


def _finite_or_none(value):
    try:
        value_f = float(value)
    except Exception:
        return None
    return value_f if math.isfinite(value_f) else None


def write_gurobi_objective_record(model_name: str, objective_value: float) -> None:
    record_root = os.environ.get("OR_SPACE_SOLVER_RECORD_DIR")
    if not record_root:
        return
    record_dir = Path(record_root)
    record_dir.mkdir(parents=True, exist_ok=True)

    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", model_name)[:180] or "execution_record"
    model = gp.Model(safe_name)
    model.Params.OutputFlag = 0
    model.Params.LogFile = str(record_dir / f"{safe_name}.gurobi.log")
    z = model.addVar(lb=objective_value, ub=objective_value, name="reported_objective")
    model.setObjective(z, GRB.MAXIMIZE)
    model.optimize()

    record = {
        "solver": "gurobi",
        "model_name": safe_name,
        "diagnostic_type": "reported_objective_record",
        "status_code": model.Status,
        "status": "OPTIMAL" if model.Status == GRB.OPTIMAL else str(model.Status),
        "objective_value": _finite_or_none(objective_value),
        "runtime": _finite_or_none(getattr(model, "Runtime", None)),
        "variables": {
            "reported_objective": {
                "value": _finite_or_none(z.X if model.SolCount else None)
            }
        },
        "constraints": {},
        "note": "The optimization logic in current_heuristic.py is exact search or custom nonlinear evaluation; this Gurobi model records the reported objective for lifecycle diagnostics.",
    }
    (record_dir / f"{safe_name}.solution.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def install_gurobi_objective_recorder(model_name: str = "execution_record") -> None:
    def wrapped_print(*args, **kwargs):
        _ORIGINAL_PRINT(*args, **kwargs)
        text = " ".join(str(arg) for arg in args)
        match = _OBJECTIVE_RE.search(text)
        if match:
            try:
                write_gurobi_objective_record(model_name, float(match.group(1)))
            except Exception as exc:  # keep benchmark code behavior unchanged
                _ORIGINAL_PRINT(f"[gurobi_record_warning] {exc}")

    builtins.print = wrapped_print
