import os
import csv
import gurobi_pulp_compat as pulp

def solve():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

    # Read general parameters
    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name']] = float(row['Value'])

    # Read product segments and profits
    products = []
    segments = {}
    with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
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

    prob = pulp.LpProblem("Maximize_Profit", pulp.LpMaximize)
    M = 10000

    x = {}
    p_var = {}
    y = {}

    for prod in products:
        pname = prod.split('_')[1]
        x[prod] = pulp.LpVariable(f"x_{pname}", lowBound=0, cat='Integer')
        p_var[prod] = pulp.LpVariable(f"p_{pname}", lowBound=0)
        y[prod] = []
        for i in range(len(segments[prod])):
            yi = pulp.LpVariable(f"y_{pname}_{i}", cat='Binary')
            y[prod].append(yi)

    # Objective
    prob += pulp.lpSum(p_var[prod] for prod in products)

    for prod in products:
        segs = segments[prod]
        # Mutual exclusivity: at most one segment active
        prob += pulp.lpSum(y[prod]) <= 1

        for i, seg in enumerate(segs):
            lo = seg['lower']
            hi = seg['upper']
            profit = seg['profit']

            # If y[i]=1, x must be in [lo+1, hi] (or [lo+1, inf] for last segment)
            if lo == 0:
                prob += x[prod] >= 1 - M * (1 - y[prod][i])
            else:
                prob += x[prod] >= (lo + 1) - M * (1 - y[prod][i])

            if hi is not None:
                prob += x[prod] <= hi + M * (1 - y[prod][i])

            # Profit bound
            prob += p_var[prod] <= profit * x[prod] + M * (1 - y[prod][i])

        # If no segment active (production=0), force x=0 and profit=0
        prob += x[prod] <= M * pulp.lpSum(y[prod])
        prob += p_var[prod] <= M * pulp.lpSum(y[prod])

    # Resource constraints
    for res_prefix, res_limit in [
        ('technical_prep_time', 'available_technical_prep_time'),
        ('labor_time', 'available_labor_time'),
        ('materials', 'available_materials')
    ]:
        prob += pulp.lpSum(
            params[f"{res_prefix}_{prod.split('_')[1]}"] * x[prod]
            for prod in products
        ) <= params[res_limit]

    prob.solve(pulp.GUROBI_CMD(msg=0))

    obj = pulp.value(prob.objective)
    if obj is not None:
        print(f"OBJECTIVE_VALUE: {round(obj, 2)}")
    else:
        print("OBJECTIVE_VALUE: None")

if __name__ == "__main__":
    solve()
