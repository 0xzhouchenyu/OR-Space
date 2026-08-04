import os
import pandas as pd
import gurobi_pulp_compat as pulp

def solve():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

    gp = pd.read_csv(os.path.join(data_dir, 'general_parameters.csv'))
    params = {row['Parameter_Name']: float(row['Value']) for _, row in gp.iterrows()}

    tbl = pd.read_csv(os.path.join(data_dir, 'table_1.csv'))
    products = []
    segments = {}
    for _, row in tbl.iterrows():
        p = row['Product']
        if p not in segments:
            segments[p] = []
            products.append(p)
        rng = row['Sales_Volume_Range']
        profit = float(row['Profit'])
        if rng.startswith('Above_'):
            lower = float(rng.split('_')[1])
            upper = None
        else:
            parts = rng.split('_')
            lower = float(parts[0])
            upper = float(parts[1])
        segments[p].append({'lower': lower, 'upper': upper, 'profit': profit})

    prob = pulp.LpProblem("Maximize_Profit_Revised", pulp.LpMaximize)
    M = 10000

    x = {}
    p_var = {}
    y = {}
    for prod in products:
        pname = prod.split('_')[1]
        x[prod] = pulp.LpVariable(f"x_{pname}", lowBound=0, cat='Integer')
        p_var[prod] = pulp.LpVariable(f"p_{pname}", lowBound=0)
        y[prod] = [pulp.LpVariable(f"y_{pname}_{i}", cat='Binary') for i in range(len(segments[prod]))]

    L_reg = pulp.LpVariable("L_reg", lowBound=0)
    L_ot  = pulp.LpVariable("L_ot", lowBound=0)
    overtime_second_review = pulp.LpVariable("overtime_second_review", cat='Binary')

    # Objective: segment profits minus overtime cost
    prob += pulp.lpSum(p_var[prod] for prod in products) - params['overtime_cost_per_hour'] * L_ot - params['overtime_second_review_fee'] * overtime_second_review

    # Segment logic (unchanged)
    for prod in products:
        segs = segments[prod]
        prob += pulp.lpSum(y[prod]) <= 1
        for i, seg in enumerate(segs):
            lo = seg['lower']; hi = seg['upper']; profit = seg['profit']
            if lo == 0:
                prob += x[prod] >= 1 - M * (1 - y[prod][i])
            else:
                prob += x[prod] >= (lo + 1) - M * (1 - y[prod][i])
            if hi is not None:
                prob += x[prod] <= hi + M * (1 - y[prod][i])
            prob += p_var[prod] <= profit * x[prod] + M * (1 - y[prod][i])
        prob += x[prod] <= M * pulp.lpSum(y[prod])
        prob += p_var[prod] <= M * pulp.lpSum(y[prod])

    # Technical prep constraint (unchanged)
    prob += pulp.lpSum(
        params[f"technical_prep_time_{prod.split('_')[1]}"] * x[prod] for prod in products
    ) <= params['available_technical_prep_time']

    # Materials constraint (unchanged)
    prob += pulp.lpSum(
        params[f"materials_{prod.split('_')[1]}"] * x[prod] for prod in products
    ) <= params['available_materials']

    # Labor: split into regular + overtime
    prob += L_reg + L_ot == pulp.lpSum(
        params[f"labor_time_{prod.split('_')[1]}"] * x[prod] for prod in products
    )
    prob += L_reg <= params['available_labor_time']
    prob += L_ot  <= params['overtime_cap_hours']
    prob += L_ot <= params['overtime_second_review_threshold'] + params['overtime_cap_hours'] * overtime_second_review

    # Shared packaging capacity
    prob += pulp.lpSum(
        params[f"pack_units_{prod.split('_')[1]}"] * x[prod] for prod in products
    ) <= params['packaging_cap_units']

    prob.solve(pulp.GUROBI_CMD(msg=0))

    obj = pulp.value(prob.objective)
    value = round(obj, 2) if obj is not None else None
    print(f"OBJECTIVE_VALUE: {value}")

if __name__ == "__main__":
    solve()
