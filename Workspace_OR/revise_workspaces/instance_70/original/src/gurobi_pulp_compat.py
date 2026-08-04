"""Small PuLP-compatible modeling surface backed by gurobipy.

This module is intentionally narrow: it supports the PuLP subset used by the
OR-Space generated reference programs, while solving through Gurobi and writing
structured solver records when requested via environment variables.
"""
from __future__ import annotations

import json
import math
import numbers
import os
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable

import gurobipy as gp
from gurobipy import GRB


LpMinimize = 1
LpMaximize = -1
LpContinuous = "Continuous"
LpInteger = "Integer"
LpBinary = "Binary"

LpStatusOptimal = 1
LpStatusNotSolved = 0
LpStatusInfeasible = -1
LpStatusUnbounded = -2
LpStatusUndefined = -3

LpStatus = {
    LpStatusOptimal: "Optimal",
    LpStatusNotSolved: "Not Solved",
    LpStatusInfeasible: "Infeasible",
    LpStatusUnbounded: "Unbounded",
    LpStatusUndefined: "Undefined",
}

constants = SimpleNamespace(
    LpStatusOptimal=LpStatusOptimal,
    LpStatusNotSolved=LpStatusNotSolved,
    LpStatusInfeasible=LpStatusInfeasible,
    LpStatusUnbounded=LpStatusUnbounded,
    LpStatusUndefined=LpStatusUndefined,
)


def _clean_name(name: Any) -> str:
    raw = str(name)
    raw = raw.replace(" ", "_")
    raw = re.sub(r"[^A-Za-z0-9_.\\-\\[\\],()]+", "_", raw)
    return raw[:240] or "unnamed"


def _is_number(value: Any) -> bool:
    return isinstance(value, numbers.Number)


def _as_expr(value: Any) -> "LpAffineExpression":
    if isinstance(value, LpAffineExpression):
        return value
    if isinstance(value, LpVariable):
        return LpAffineExpression({value: 1.0}, 0.0)
    if _is_number(value):
        return LpAffineExpression({}, float(value))
    raise TypeError(f"Cannot convert {type(value).__name__} to a linear expression")


class LpAffineExpression:
    def __init__(self, terms: dict["LpVariable", float] | None = None, constant: float = 0.0) -> None:
        self.terms: dict[LpVariable, float] = dict(terms or {})
        self.constant = float(constant)

    def copy(self) -> "LpAffineExpression":
        return LpAffineExpression(self.terms, self.constant)

    def variables(self) -> set["LpVariable"]:
        return set(self.terms)

    def evaluate(self) -> float:
        total = self.constant
        for var, coeff in self.terms.items():
            val = 0.0 if var.varValue is None else float(var.varValue)
            total += coeff * val
        return total

    def value(self) -> float:
        return self.evaluate()

    def _combine(self, other: Any, sign: float) -> "LpAffineExpression":
        other_expr = _as_expr(other)
        result = self.copy()
        result.constant += sign * other_expr.constant
        for var, coeff in other_expr.terms.items():
            result.terms[var] = result.terms.get(var, 0.0) + sign * coeff
            if abs(result.terms[var]) < 1e-12:
                del result.terms[var]
        return result

    def __add__(self, other: Any) -> "LpAffineExpression":
        return self._combine(other, 1.0)

    def __radd__(self, other: Any) -> "LpAffineExpression":
        return _as_expr(other)._combine(self, 1.0)

    def __sub__(self, other: Any) -> "LpAffineExpression":
        return self._combine(other, -1.0)

    def __rsub__(self, other: Any) -> "LpAffineExpression":
        return _as_expr(other)._combine(self, -1.0)

    def __neg__(self) -> "LpAffineExpression":
        return self * -1.0

    def __mul__(self, other: Any) -> "LpAffineExpression":
        if not _is_number(other):
            raise TypeError("Only scalar multiplication is supported")
        factor = float(other)
        return LpAffineExpression({var: coeff * factor for var, coeff in self.terms.items()}, self.constant * factor)

    def __rmul__(self, other: Any) -> "LpAffineExpression":
        return self.__mul__(other)

    def __truediv__(self, other: Any) -> "LpAffineExpression":
        if not _is_number(other):
            raise TypeError("Only scalar division is supported")
        return self * (1.0 / float(other))

    def __le__(self, other: Any) -> "LpConstraint":
        return LpConstraint(self - other, "<=")

    def __ge__(self, other: Any) -> "LpConstraint":
        return LpConstraint(self - other, ">=")

    def __eq__(self, other: Any) -> "LpConstraint":  # type: ignore[override]
        return LpConstraint(self - other, "==")

    def __bool__(self) -> bool:
        raise TypeError("Linear expressions cannot be used as booleans")

    def __repr__(self) -> str:
        chunks = [f"{coef}*{var.name}" for var, coef in self.terms.items()]
        if self.constant:
            chunks.append(str(self.constant))
        return " + ".join(chunks) if chunks else "0"


class LpVariable:
    def __init__(
        self,
        name: str,
        lowBound: float | None = None,
        upBound: float | None = None,
        cat: str = LpContinuous,
        **_: Any,
    ) -> None:
        self.name = str(name)
        self.lowBound = lowBound
        self.upBound = upBound
        self.cat = cat
        self.varValue: float | None = None
        self._start: float | None = None
        self._gp_var: gp.Var | None = None

    def __hash__(self) -> int:
        return id(self)

    def __add__(self, other: Any) -> LpAffineExpression:
        return _as_expr(self) + other

    def __radd__(self, other: Any) -> LpAffineExpression:
        return _as_expr(other) + self

    def __sub__(self, other: Any) -> LpAffineExpression:
        return _as_expr(self) - other

    def __rsub__(self, other: Any) -> LpAffineExpression:
        return _as_expr(other) - self

    def __mul__(self, other: Any) -> LpAffineExpression:
        return _as_expr(self) * other

    def __rmul__(self, other: Any) -> LpAffineExpression:
        return _as_expr(self) * other

    def __truediv__(self, other: Any) -> LpAffineExpression:
        return _as_expr(self) / other

    def __neg__(self) -> LpAffineExpression:
        return -_as_expr(self)

    def __le__(self, other: Any) -> "LpConstraint":
        return _as_expr(self) <= other

    def __ge__(self, other: Any) -> "LpConstraint":
        return _as_expr(self) >= other

    def __eq__(self, other: Any) -> "LpConstraint":  # type: ignore[override]
        return _as_expr(self) == other

    def value(self) -> float | None:
        return self.varValue

    def setInitialValue(self, value: float, *_: Any, **__: Any) -> bool:
        self._start = float(value)
        return True

    @staticmethod
    def dicts(
        name: str,
        indices: Iterable[Any] | tuple[Iterable[Any], ...],
        lowBound: float | None = None,
        upBound: float | None = None,
        cat: str = LpContinuous,
        **kwargs: Any,
    ) -> dict[Any, Any]:
        if isinstance(indices, tuple) and not (indices and isinstance(indices[0], tuple)):
            index_sets = [list(index_set) for index_set in indices]

            def build(prefix: list[Any], rest: list[list[Any]]) -> dict[Any, Any]:
                current = {}
                for idx in rest[0]:
                    next_prefix = prefix + [idx]
                    if len(rest) == 1:
                        suffix = "_".join(_clean_name(part) for part in next_prefix)
                        current[idx] = LpVariable(f"{name}_{suffix}", lowBound=lowBound, upBound=upBound, cat=cat, **kwargs)
                    else:
                        current[idx] = build(next_prefix, rest[1:])
                return current

            return build([], index_sets)

        return {
            idx: LpVariable(f"{name}_{_clean_name(idx)}", lowBound=lowBound, upBound=upBound, cat=cat, **kwargs)
            for idx in list(indices)
        }

    def __repr__(self) -> str:
        return self.name


class LpConstraint:
    def __init__(self, expr: LpAffineExpression, sense: str, name: str | None = None) -> None:
        self.expr = expr
        self.sense = sense
        self.name = name
        self.slack: float | None = None
        self.pi: float | None = None

    def variables(self) -> set[LpVariable]:
        return self.expr.variables()


def lpSum(items: Iterable[Any]) -> LpAffineExpression:
    result = LpAffineExpression()
    for item in items:
        result += item
    return result


def value(item: Any) -> float | None:
    if item is None:
        return None
    if isinstance(item, LpVariable):
        return item.varValue
    if isinstance(item, LpAffineExpression):
        return item.evaluate()
    if isinstance(item, LpConstraint):
        return item.expr.evaluate()
    if _is_number(item):
        return float(item)
    return item


class GUROBI_CMD:
    def __init__(self, msg: bool | int = True, timeLimit: float | None = None, **_: Any) -> None:
        self.msg = bool(msg)
        self.timeLimit = timeLimit


GUROBI_CMD = GUROBI_CMD
GUROBI = GUROBI_CMD


class LpProblem:
    def __init__(self, name: str = "model", sense: int = LpMinimize) -> None:
        self.name = name
        self.sense = sense
        self.objective: LpAffineExpression | None = None
        self.constraints: dict[str, LpConstraint] = {}
        self.status = LpStatusNotSolved
        self.solverModel: gp.Model | None = None
        self._constraint_count = 0
        self._variables: list[LpVariable] = []

    def __iadd__(self, item: Any) -> "LpProblem":
        name = None
        payload = item
        if isinstance(item, tuple) and len(item) == 2 and isinstance(item[1], str):
            payload, name = item
        if isinstance(payload, LpConstraint):
            self._constraint_count += 1
            cname = name or payload.name or f"_C{self._constraint_count}"
            payload.name = cname
            self.constraints[cname] = payload
        else:
            self.objective = _as_expr(payload)
        return self

    def variables(self) -> list[LpVariable]:
        if self._variables:
            return list(self._variables)
        seen: set[LpVariable] = set()
        if self.objective is not None:
            seen.update(self.objective.variables())
        for constr in self.constraints.values():
            seen.update(constr.variables())
        return sorted(seen, key=lambda var: var.name)

    def _to_gp_expr(self, expr: LpAffineExpression, var_map: dict[LpVariable, gp.Var]) -> gp.LinExpr:
        gp_expr = gp.LinExpr(expr.constant)
        for var, coeff in expr.terms.items():
            gp_expr.add(var_map[var], coeff)
        return gp_expr

    def solve(self, solver: GUROBI_CMD | None = None, **_: Any) -> int:
        solver = solver or GUROBI_CMD(msg=False)
        model = gp.Model(_clean_name(self.name))
        model.Params.OutputFlag = 1 if getattr(solver, "msg", False) else 0
        if getattr(solver, "timeLimit", None):
            model.Params.TimeLimit = float(solver.timeLimit)

        record_dir = os.environ.get("OR_SPACE_SOLVER_RECORD_DIR")
        log_path = None
        if record_dir:
            Path(record_dir).mkdir(parents=True, exist_ok=True)
            log_path = Path(record_dir) / f"{_clean_name(self.name)}.gurobi.log"
            model.Params.LogFile = str(log_path)

        variables = self.variables()
        var_map: dict[LpVariable, gp.Var] = {}
        used_names: set[str] = set()
        for var in variables:
            lb = -GRB.INFINITY if var.lowBound is None else float(var.lowBound)
            ub = GRB.INFINITY if var.upBound is None else float(var.upBound)
            vtype = GRB.CONTINUOUS
            cat = var.cat
            if cat in (LpBinary, "Binary"):
                vtype = GRB.BINARY
                lb = max(lb, 0.0)
                ub = min(ub, 1.0)
            elif cat in (LpInteger, "Integer"):
                vtype = GRB.INTEGER
            base_name = _clean_name(var.name)
            gp_name = base_name
            suffix = 1
            while gp_name in used_names:
                suffix += 1
                gp_name = f"{base_name}_{suffix}"
            used_names.add(gp_name)
            gp_var = model.addVar(lb=lb, ub=ub, vtype=vtype, name=gp_name)
            if var._start is not None:
                gp_var.Start = var._start
            var._gp_var = gp_var
            var_map[var] = gp_var

        model.update()

        if self.objective is None:
            self.objective = LpAffineExpression()
        obj = self._to_gp_expr(self.objective, var_map)
        model.setObjective(obj, GRB.MINIMIZE if self.sense == LpMinimize else GRB.MAXIMIZE)

        gp_constraints: dict[str, gp.Constr] = {}
        for cname, constr in self.constraints.items():
            gp_expr = self._to_gp_expr(constr.expr, var_map)
            safe_name = _clean_name(cname)
            if constr.sense == "<=":
                gp_constraints[cname] = model.addConstr(gp_expr <= 0.0, name=safe_name)
            elif constr.sense == ">=":
                gp_constraints[cname] = model.addConstr(gp_expr >= 0.0, name=safe_name)
            elif constr.sense == "==":
                gp_constraints[cname] = model.addConstr(gp_expr == 0.0, name=safe_name)
            else:
                raise ValueError(f"Unknown constraint sense: {constr.sense}")

        model.optimize()
        self.solverModel = model
        self._variables = variables
        self.status = _status_from_gurobi(model.Status)

        if model.SolCount:
            for var in variables:
                if var._gp_var is not None:
                    val = var._gp_var.X
                    if var.cat in (LpBinary, "Binary", LpInteger, "Integer") and abs(val - round(val)) < 1e-6:
                        val = round(val)
                    var.varValue = val

        for cname, constr in self.constraints.items():
            gp_constr = gp_constraints[cname]
            try:
                constr.slack = gp_constr.Slack
            except Exception:
                constr.slack = None
            try:
                constr.pi = gp_constr.Pi
            except Exception:
                constr.pi = None

        if record_dir:
            _write_solution_record(Path(record_dir), self, model, gp_constraints, log_path)
            if os.environ.get("OR_SPACE_WRITE_RELAXATION", "1") == "1" and model.IsMIP:
                _write_relaxation_record(Path(record_dir), self, model)

        return self.status


def _status_from_gurobi(status: int) -> int:
    if status == GRB.OPTIMAL:
        return LpStatusOptimal
    if status == GRB.INFEASIBLE:
        return LpStatusInfeasible
    if status == GRB.UNBOUNDED:
        return LpStatusUnbounded
    if status == GRB.INF_OR_UNBD:
        return LpStatusUndefined
    return LpStatusNotSolved


def _finite_or_none(value_: float | int | None) -> float | int | None:
    if value_ is None:
        return None
    try:
        value_f = float(value_)
    except Exception:
        return None
    if math.isfinite(value_f):
        return value_f
    return None


def _write_solution_record(
    record_dir: Path,
    problem: LpProblem,
    model: gp.Model,
    gp_constraints: dict[str, gp.Constr],
    log_path: Path | None,
) -> None:
    record: dict[str, Any] = {
        "solver": "gurobi",
        "model_name": problem.name,
        "status_code": model.Status,
        "status": GRB.Status.__dict__.get(model.Status, str(model.Status)) if hasattr(GRB, "Status") else str(model.Status),
        "pulp_status_code": problem.status,
        "pulp_status": LpStatus.get(problem.status, "Unknown"),
        "is_mip": bool(model.IsMIP),
        "objective_value": _finite_or_none(model.ObjVal if model.SolCount else None),
        "objective_bound": _finite_or_none(getattr(model, "ObjBound", None)),
        "mip_gap": _finite_or_none(getattr(model, "MIPGap", None)) if model.IsMIP and model.SolCount else None,
        "runtime": _finite_or_none(getattr(model, "Runtime", None)),
        "node_count": _finite_or_none(getattr(model, "NodeCount", None)),
        "iteration_count": _finite_or_none(getattr(model, "IterCount", None)),
        "barrier_iteration_count": _finite_or_none(getattr(model, "BarIterCount", None)),
        "log_file": str(log_path) if log_path else None,
        "variables": {},
        "constraints": {},
    }
    if model.SolCount:
        for var in problem.variables():
            gp_var = var._gp_var
            if gp_var is None:
                continue
            item: dict[str, Any] = {"value": _finite_or_none(gp_var.X)}
            try:
                item["reduced_cost"] = _finite_or_none(gp_var.RC)
            except Exception:
                item["reduced_cost"] = None
            record["variables"][var.name] = item
        for cname, constr in problem.constraints.items():
            gp_constr = gp_constraints[cname]
            item = {"sense": constr.sense}
            try:
                item["slack"] = _finite_or_none(gp_constr.Slack)
            except Exception:
                item["slack"] = None
            try:
                item["dual_value"] = _finite_or_none(gp_constr.Pi)
            except Exception:
                item["dual_value"] = None
            record["constraints"][cname] = item

    (record_dir / f"{_clean_name(problem.name)}.solution.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _write_relaxation_record(record_dir: Path, problem: LpProblem, model: gp.Model) -> None:
    rel = model.relax()
    rel.Params.OutputFlag = 0
    rel.optimize()
    record: dict[str, Any] = {
        "solver": "gurobi",
        "model_name": f"{problem.name}_lp_relaxation",
        "diagnostic_type": "lp_relaxation",
        "status_code": rel.Status,
        "objective_value": _finite_or_none(rel.ObjVal if rel.SolCount else None),
        "runtime": _finite_or_none(getattr(rel, "Runtime", None)),
        "variables": {},
        "constraints": {},
    }
    if rel.SolCount:
        for var in rel.getVars():
            item: dict[str, Any] = {"value": _finite_or_none(var.X)}
            try:
                item["reduced_cost"] = _finite_or_none(var.RC)
            except Exception:
                item["reduced_cost"] = None
            record["variables"][var.VarName] = item
        for constr in rel.getConstrs():
            item = {"sense": constr.Sense}
            try:
                item["slack"] = _finite_or_none(constr.Slack)
                item["dual_value"] = _finite_or_none(constr.Pi)
            except Exception:
                item["slack"] = None
                item["dual_value"] = None
            record["constraints"][constr.ConstrName] = item

    (record_dir / f"{_clean_name(problem.name)}.lp_relaxation.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


__all__ = [
    "LpProblem",
    "LpVariable",
    "LpMinimize",
    "LpMaximize",
    "LpContinuous",
    "LpInteger",
    "LpBinary",
    "LpStatus",
    "LpStatusOptimal",
    "LpStatusNotSolved",
    "LpStatusInfeasible",
    "LpStatusUnbounded",
    "LpStatusUndefined",
    "GUROBI_CMD",
    "GUROBI_CMD",
    "GUROBI",
    "lpSum",
    "value",
    "constants",
]
