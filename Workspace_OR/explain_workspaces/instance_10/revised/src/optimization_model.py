import os
import pandas as pd
from gurobi_pulp_compat import LpProblem, LpMinimize, LpVariable, lpSum, GUROBI_CMD, value, LpStatus

def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

    # Load coverage table
    raw = pd.read_csv(os.path.join(data_dir, 'table_1.csv'), header=None, skiprows=1, dtype=str).fillna('')
    coverage = {}
    areas = []
    for _, row in raw.iterrows():
        code = str(row.iloc[0]).strip()
        if not code:
            continue
        areas.append(code)
        joined = ','.join(str(x) for x in row.iloc[1:].tolist())
        cov = {tok.strip() for tok in joined.split(',') if tok.strip()}
        coverage[code] = cov

    # Load parameters
    pdf = pd.read_csv(os.path.join(data_dir, 'general_parameters.csv'))
    params = {r['Parameter_Name'].strip(): r['Value'] for _, r in pdf.iterrows()}
    small_cost = float(params['small_cost'])
    large_cost = float(params['large_cost'])
    small_cap = int(float(params['small_cap_areas']))
    max_large = int(float(params['max_large_stores']))
    min_counters = float(params['minimum_neighborhood_counters'])
    counter_credit = float(params['small_store_counter_credit'])

    all_residential = set()
    for j in areas:
        all_residential |= coverage[j]

    prob = LpProblem('FranchiseTieredCovering', LpMinimize)

    s = {j: LpVariable(f's_{j}', cat='Binary') for j in areas}
    l = {j: LpVariable(f'l_{j}', cat='Binary') for j in areas}
    a = {(j, i): LpVariable(f'a_{j}_{i}', cat='Binary')
         for j in areas for i in coverage[j]}

    # Objective
    prob += lpSum(small_cost * s[j] + large_cost * l[j] for j in areas)

    # (C1) Mode exclusivity
    for j in areas:
        prob += s[j] + l[j] <= 1, f'mode_excl_{j}'

    # (C2) Assignment requires open store
    for (j, i) in a:
        prob += a[(j, i)] <= s[j] + l[j], f'assign_open_{j}_{i}'

    # (C3) Small-store capacity (Large unrestricted up to |cov(j)|)
    for j in areas:
        cj = len(coverage[j])
        prob += lpSum(a[(j, i)] for i in coverage[j]) <= small_cap * s[j] + cj * l[j], f'small_cap_{j}'

    # (C4) Coverage requirement
    for i in all_residential:
        covering = [j for j in areas if i in coverage[j]]
        prob += lpSum(a[(j, i)] for j in covering) >= 1, f'cover_{i}'

    # (C5) Regulatory cap on Large stores
    prob += lpSum(l[j] for j in areas) <= max_large, 'large_cap'

    # City-facing neighborhood counter promise
    prob += counter_credit * lpSum(s[j] for j in areas) >= min_counters, 'neighborhood_counter_commitment'

    prob.solve(GUROBI_CMD(msg=0))

    print(f'Status: {LpStatus[prob.status]}')
    for j in areas:
        if value(s[j]) > 0.5:
            served = [i for i in coverage[j] if value(a[(j, i)]) > 0.5]
            print(f'  Small store at {j} serves {sorted(served)}')
        if value(l[j]) > 0.5:
            served = [i for i in coverage[j] if value(a[(j, i)]) > 0.5]
            print(f'  Large store at {j} serves {sorted(served)}')

    obj = value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj}")

if __name__ == '__main__':
    main()
