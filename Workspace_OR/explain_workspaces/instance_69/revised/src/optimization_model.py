import os
import pandas as pd
import gurobi_pulp_compat as pulp

def solve():
    data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'general_parameters.csv')
    df = pd.read_csv(data_path)

    params = {}
    for _, row in df.iterrows():
        params[row['Parameter_Name']] = row['Value']

    q3 = int(float(params['batch_3m_quantity']))
    q4 = int(float(params['batch_4m_quantity']))
    q5 = int(float(params['batch_5m_quantity']))
    L = int(float(params['raw_bar_length']))
    setup_cost = float(params['setup_cost_per_pattern'])
    max_patterns = int(float(params['max_distinct_patterns']))

    len1, len2, len3 = 3, 4, 5

    # Generate all valid cutting patterns (a,b,c)
    patterns = []
    for a in range(L // len1 + 1):
        for b in range(L // len2 + 1):
            for c in range(L // len3 + 1):
                if len1 * a + len2 * b + len3 * c <= L and (a + b + c) >= 1:
                    patterns.append((a, b, c))

    # Big-M upper bound for n_p: total demand suffices
    M = q3 + q4 + q5

    prob = pulp.LpProblem("CuttingStock_Revised", pulp.LpMinimize)

    n = pulp.LpVariable.dicts("n", range(len(patterns)), lowBound=0, cat='Integer')
    u = pulp.LpVariable.dicts("u", range(len(patterns)), lowBound=0, upBound=1, cat='Binary')

    # Objective: trim loss + overproduction + setup waste
    prob += (pulp.lpSum(L * n[i] for i in range(len(patterns)))
             - (len1 * q3 + len2 * q4 + len3 * q5)
             + setup_cost * pulp.lpSum(u[i] for i in range(len(patterns))))

    # Demand constraints
    prob += pulp.lpSum(patterns[i][0] * n[i] for i in range(len(patterns))) >= q3
    prob += pulp.lpSum(patterns[i][1] * n[i] for i in range(len(patterns))) >= q4
    prob += pulp.lpSum(patterns[i][2] * n[i] for i in range(len(patterns))) >= q5

    # Linking n_p <= M * u_p
    for i in range(len(patterns)):
        prob += n[i] <= M * u[i]

    # Pattern diversity cap
    prob += pulp.lpSum(u[i] for i in range(len(patterns))) <= max_patterns

    prob.solve(pulp.GUROBI_CMD(msg=False))

    obj_val = pulp.value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    solve()