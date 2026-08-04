import gurobi_pulp_compat as pulp
import pandas as pd
import os

def solve():
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'general_parameters.csv')
    df = pd.read_csv(csv_path)
    params = dict(zip(df['Parameter_Name'], df['Value']))

    commodities = ['steel', 'engine', 'electronics', 'plastic']

    # Decision variables
    x = {c: pulp.LpVariable(f"x_{c}", lowBound=0) for c in commodities}
    imp = {c: pulp.LpVariable(f"imp_{c}", lowBound=0, upBound=float(params['import_quota'])) for c in commodities}
    L_reg = pulp.LpVariable("L_reg", lowBound=0, upBound=float(params['labor_force']))
    L_ot = pulp.LpVariable("L_ot", lowBound=0, upBound=float(params['overtime_cap']))

    # Production upper bounds
    for c in commodities:
        key = f"{c}_production_limit"
        if key in params:
            x[c].upBound = float(params[key])

    model = pulp.LpProblem("Maximize_GDP_Revised", pulp.LpMaximize)

    # Net export = x_c + imp_c - consumption_c
    net_export = {}
    for c in commodities:
        consumed = pulp.lpSum(
            float(params.get(f"{cp}_{c}_requirement", 0.0)) * x[cp]
            for cp in commodities
        )
        net_export[c] = x[c] + imp[c] - consumed

    # Domestic demand satisfaction
    for c in commodities:
        model += net_export[c] >= 0, f"Domestic_Demand_{c}"

    # Labor regulation: L_reg + L_ot = total labor used
    total_labor = pulp.lpSum(float(params[f"{c}_labor_requirement"]) * x[c] for c in commodities)
    model += L_reg + L_ot == total_labor, "Labor_Balance"
    # (Caps already enforced by upBound on L_reg and L_ot)

    # Objective
    export_revenue = pulp.lpSum(float(params[f"{c}_price"]) * net_export[c] for c in commodities)
    domestic_import_cost = pulp.lpSum(float(params[f"{c}_import_cost"]) * x[c] for c in commodities)
    finished_import_cost = pulp.lpSum(
        float(params['import_premium_ratio']) * float(params[f"{c}_price"]) * imp[c]
        for c in commodities
    )
    overtime_cost = float(params['overtime_wage']) * L_ot

    model += export_revenue - domestic_import_cost - finished_import_cost - overtime_cost

    model.solve(pulp.GUROBI_CMD(msg=False))

    return pulp.value(model.objective)

if __name__ == '__main__':
    result = solve()
    value = round(result, 3) if result is not None else None
    print(f"OBJECTIVE_VALUE: {value}")
