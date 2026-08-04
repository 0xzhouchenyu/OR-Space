import os
import pandas as pd
import gurobi_pulp_compat as pulp
from utils import get_data_paths

def solve():
    table_1_path, params_path = get_data_paths()

    df_items = pd.read_csv(table_1_path)
    df_params = pd.read_csv(params_path)

    params = {}
    for _, row in df_params.iterrows():
        params[row['Parameter_Name']] = row['Value']

    raw_pipe_length = float(params['raw_pipe_length'])
    max_patterns = int(params['max_cutting_patterns'])
    max_cuts = int(params['max_cuts_per_pipe'])
    max_leftover = float(params['max_leftover_length'])
    min_length = raw_pipe_length - max_leftover

    cost_rates = []
    rank_prefixes = ['most', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth', 'tenth']
    for prefix in rank_prefixes:
        key = f"{prefix}_frequent_pattern_cost_rate"
        if key in params:
            cost_rates.append(float(params[key]))
        else:
            break

    lengths = df_items['Length'].tolist()
    demands = df_items['Quantity'].tolist()
    n_items = len(lengths)

    patterns = []
    def generate_patterns(current_pattern, current_length, current_cuts, item_idx):
        if item_idx == n_items:
            if current_length >= min_length and current_length <= raw_pipe_length and current_cuts > 0:
                patterns.append(tuple(current_pattern))
            return
        
        max_qty = min(
            int((raw_pipe_length - current_length) // lengths[item_idx]),
            max_cuts - current_cuts
        )
        
        for q in range(max_qty + 1):
            generate_patterns(
                current_pattern + [q],
                current_length + q * lengths[item_idx],
                current_cuts + q,
                item_idx + 1
            )

    generate_patterns([], 0, 0, 0)

    prob = pulp.LpProblem("Pipe_Cutting", pulp.LpMinimize)

    y = pulp.LpVariable.dicts("y", range(len(patterns)), lowBound=0, cat='Integer')
    z = pulp.LpVariable.dicts("z", range(len(patterns)), cat='Binary')
    u = pulp.LpVariable.dicts("u", range(1, max_patterns + 1), cat='Binary')

    extra_cost = 0
    for k in range(1, max_patterns + 1):
        if k - 1 < len(cost_rates):
            extra_cost += cost_rates[k - 1] * u[k]

    prob += pulp.lpSum([y[p] for p in range(len(patterns))]) + extra_cost

    for i in range(n_items):
        prob += pulp.lpSum([patterns[p][i] * y[p] for p in range(len(patterns))]) >= demands[i]

    M = sum(demands)
    for p in range(len(patterns)):
        prob += y[p] <= M * z[p]

    prob += pulp.lpSum([z[p] for p in range(len(patterns))]) == pulp.lpSum([u[k] for k in range(1, max_patterns + 1)])

    for k in range(1, max_patterns):
        prob += u[k] >= u[k+1]

    prob += pulp.lpSum([z[p] for p in range(len(patterns))]) <= max_patterns

    prob.solve(pulp.GUROBI_CMD(msg=False))

    print(f"OBJECTIVE_VALUE: {pulp.value(prob.objective)}")

if __name__ == "__main__":
    solve()