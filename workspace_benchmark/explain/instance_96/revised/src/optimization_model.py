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
        params[str(row['Parameter_Name'])] = row['Value']

    # Read supplier-specific parameters
    L1 = float(params['raw_pipe_length_supplier1'])
    L2 = float(params['raw_pipe_length_supplier2'])

    max_patterns_s1 = int(params['max_cutting_patterns_supplier1'])
    max_patterns_s2 = int(params['max_cutting_patterns_supplier2'])

    max_cuts_s1 = int(params['max_cuts_per_pipe_supplier1'])
    max_cuts_s2 = int(params['max_cuts_per_pipe_supplier2'])

    max_leftover_s1 = float(params['max_leftover_length_supplier1'])
    max_leftover_s2 = float(params['max_leftover_length_supplier2'])

    min_len_s1 = L1 - max_leftover_s1
    min_len_s2 = L2 - max_leftover_s2

    # Pattern cost rates per supplier (up to 3 ranks used as provided)
    cost_rates_s1 = []
    for prefix in ['most', 'second', 'third']:
        key = f"{prefix}_frequent_pattern_cost_rate_supplier1"
        if key in params:
            cost_rates_s1.append(float(params[key]))

    cost_rates_s2 = []
    for prefix in ['most', 'second', 'third']:
        key = f"{prefix}_frequent_pattern_cost_rate_supplier2"
        if key in params:
            cost_rates_s2.append(float(params[key]))

    # Purchase costs
    purchase_cost_s1 = float(params['purchase_cost_per_pipe_supplier1'])
    purchase_cost_s2 = float(params['purchase_cost_per_pipe_supplier2'])

    # Discount parameters for supplier 1
    tier1_max_qty = int(params['discount_tier1_supplier1_max_qty'])
    fixed_discount_tier2 = float(params['fixed_discount_tier2_supplier1'])
    bigM_discount = float(params['bigM_discount'])

    lengths = df_items['Length'].tolist()
    demands = df_items['Quantity'].tolist()
    n_items = len(lengths)

    total_demand = int(sum(demands))

    # Generate patterns for each supplier
    patterns_s1 = []

    def gen_patterns_s1(current_pattern, current_length, current_cuts, item_idx):
        if item_idx == n_items:
            if current_cuts > 0 and current_length >= min_len_s1 and current_length <= L1:
                patterns_s1.append(tuple(current_pattern))
            return
        max_qty = min(int((L1 - current_length) // lengths[item_idx]), max_cuts_s1 - current_cuts)
        for q in range(max_qty + 1):
            gen_patterns_s1(current_pattern + [q], current_length + q * lengths[item_idx], current_cuts + q, item_idx + 1)

    gen_patterns_s1([], 0, 0, 0)

    patterns_s2 = []

    def gen_patterns_s2(current_pattern, current_length, current_cuts, item_idx):
        if item_idx == n_items:
            if current_cuts > 0 and current_length >= min_len_s2 and current_length <= L2:
                patterns_s2.append(tuple(current_pattern))
            return
        max_qty = min(int((L2 - current_length) // lengths[item_idx]), max_cuts_s2 - current_cuts)
        for q in range(max_qty + 1):
            gen_patterns_s2(current_pattern + [q], current_length + q * lengths[item_idx], current_cuts + q, item_idx + 1)

    gen_patterns_s2([], 0, 0, 0)

    P1 = range(len(patterns_s1))
    P2 = range(len(patterns_s2))

    # Build MILP
    prob = pulp.LpProblem('Two_Supplier_Pipe_Cutting', pulp.LpMinimize)

    # Decision variables
    # Pattern usage counts
    y1 = pulp.LpVariable.dicts('y1', P1, lowBound=0, cat='Integer')
    y2 = pulp.LpVariable.dicts('y2', P2, lowBound=0, cat='Integer')

    # Pattern usage indicators
    z1 = pulp.LpVariable.dicts('z1', P1, cat='Binary')
    z2 = pulp.LpVariable.dicts('z2', P2, cat='Binary')

    # Rank binary variables
    u1 = pulp.LpVariable.dicts('u1', range(1, max_patterns_s1 + 1), cat='Binary')
    u2 = pulp.LpVariable.dicts('u2', range(1, max_patterns_s2 + 1), cat='Binary')

    # Total pipes from each supplier
    total_pipes_s1 = pulp.LpVariable('total_pipes_s1', lowBound=0, cat='Integer')
    total_pipes_s2 = pulp.LpVariable('total_pipes_s2', lowBound=0, cat='Integer')

    # Discount tier binaries for supplier 1
    t1_low = pulp.LpVariable('t1_low', cat='Binary')
    t1_high = pulp.LpVariable('t1_high', cat='Binary')

    # Big-M for linking y and z
    bigM_y = total_demand

    # Demand satisfaction constraints (combined from both suppliers)
    for i in range(n_items):
        prob += (
            pulp.lpSum(patterns_s1[p][i] * y1[p] for p in P1) +
            pulp.lpSum(patterns_s2[p][i] * y2[p] for p in P2)
        ) >= demands[i], f'demand_item_{i}'

    # Link pattern usage and indicators for supplier 1
    for p in P1:
        prob += y1[p] <= bigM_y * z1[p], f'link_y1_z1_{p}'

    # Link pattern usage and indicators for supplier 2
    for p in P2:
        prob += y2[p] <= bigM_y * z2[p], f'link_y2_z2_{p}'

    # Pattern count equals rank count per supplier
    prob += pulp.lpSum(z1[p] for p in P1) == pulp.lpSum(u1[k] for k in range(1, max_patterns_s1 + 1)), 's1_pattern_rank_match'
    prob += pulp.lpSum(z2[p] for p in P2) == pulp.lpSum(u2[k] for k in range(1, max_patterns_s2 + 1)), 's2_pattern_rank_match'

    # Monotonicity of rank usage per supplier
    for k in range(1, max_patterns_s1):
        prob += u1[k] >= u1[k + 1], f's1_rank_monotone_{k}'
    for k in range(1, max_patterns_s2):
        prob += u2[k] >= u2[k + 1], f's2_rank_monotone_{k}'

    # Limit on maximum number of patterns per supplier
    prob += pulp.lpSum(z1[p] for p in P1) <= max_patterns_s1, 's1_max_patterns'
    prob += pulp.lpSum(z2[p] for p in P2) <= max_patterns_s2, 's2_max_patterns'

    # Total pipes from each supplier
    prob += total_pipes_s1 == pulp.lpSum(y1[p] for p in P1), 's1_total_pipes_def'
    prob += total_pipes_s2 == pulp.lpSum(y2[p] for p in P2), 's2_total_pipes_def'

    # Discount tier constraints for supplier 1
    prob += t1_low + t1_high == 1, 's1_tier_exclusivity'

    # If t1_high == 0, total_pipes_s1 <= tier1_max_qty
    prob += total_pipes_s1 <= tier1_max_qty + bigM_discount * t1_high, 's1_tier1_upper'

    # If t1_high == 1, total_pipes_s1 >= tier1_max_qty + 1
    prob += total_pipes_s1 >= tier1_max_qty + 1 - bigM_discount * (1 - t1_high), 's1_tier2_lower'

    # Objective: minimize purchase cost + pattern extra cost - discount
    purchase_cost_term = purchase_cost_s1 * total_pipes_s1 + purchase_cost_s2 * total_pipes_s2

    extra_cost_s1 = 0
    for k in range(1, max_patterns_s1 + 1):
        idx = k - 1
        if idx < len(cost_rates_s1):
            extra_cost_s1 += cost_rates_s1[idx] * u1[k]

    extra_cost_s2 = 0
    for k in range(1, max_patterns_s2 + 1):
        idx = k - 1
        if idx < len(cost_rates_s2):
            extra_cost_s2 += cost_rates_s2[idx] * u2[k]

    discount_term = fixed_discount_tier2 * t1_high

    prob += purchase_cost_term + extra_cost_s1 + extra_cost_s2 - discount_term

    # Solve with Gurobi
    prob.solve(pulp.GUROBI_CMD(msg=False))

    obj_val = pulp.value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj_val}")


if __name__ == '__main__':
    solve()
