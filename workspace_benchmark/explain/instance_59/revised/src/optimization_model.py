import os
import csv
import gurobi_pulp_compat as pulp


def read_table_1_7(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        rows = list(csv.reader(f))
    return rows


def read_general_parameters(path):
    params = {}
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['Parameter_Name'].strip()
            if name:
                params[name] = float(row['Value'])
    return params


def parse_percentage(val):
    val = (val or '').strip()
    if not val:
        return None, None
    if val.startswith('>='):
        return '>=', float(val[2:].replace('%', '')) / 100.0
    if val.startswith('<='):
        return '<=', float(val[2:].replace('%', '')) / 100.0
    return None, None


def main():
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    table_path = os.path.join(base_dir, 'table_1_7.csv')
    params_path = os.path.join(base_dir, 'general_parameters.csv')

    table = read_table_1_7(table_path)
    params = read_general_parameters(params_path)

    brands = table[0][1:4]
    raw_materials = [table[i][0] for i in range(1, 4)]

    raw_cost = []
    limits = []
    comp = {}
    for i in range(1, 4):
        row = table[i]
        raw_cost.append(float(row[4]))
        limits.append(float(row[5]))
        for j in range(1, 4):
            sign, pct = parse_percentage(row[j])
            if sign is not None:
                comp[(i - 1, j - 1)] = (sign, pct)

    proc_fee = [float(x) for x in table[4][1:4]]
    sell_price = [float(x) for x in table[5][1:4]]

    setup_cost = [
        params.get('SetupCost_A', 0.0),
        params.get('SetupCost_B', 0.0),
        params.get('SetupCost_C', 0.0),
    ]

    prob = pulp.LpProblem('CandyFactory_Revised', pulp.LpMaximize)

    x = {}
    for i in range(3):
        for j in range(3):
            x[(i, j)] = pulp.LpVariable(f'x_{i}_{j}', lowBound=0)

    y = {}
    z = {}
    M = sum(limits)
    for j in range(3):
        y[j] = pulp.LpVariable(f'y_{j}', lowBound=0)
        z[j] = pulp.LpVariable(f'z_{j}', cat='Binary')
    shared_ab_wrapper = pulp.LpVariable('shared_ab_wrapper', cat='Binary')

    for j in range(3):
        prob += y[j] == pulp.lpSum(x[(i, j)] for i in range(3))
        prob += y[j] <= M * z[j]

    prob += shared_ab_wrapper >= z[0] + z[1] - 1
    prob += shared_ab_wrapper <= z[0]
    prob += shared_ab_wrapper <= z[1]

    for i in range(3):
        prob += pulp.lpSum(x[(i, j)] for j in range(3)) <= limits[i]

    for (i, j), (sign, pct) in comp.items():
        if sign == '>=':
            prob += x[(i, j)] >= pct * y[j]
        elif sign == '<=':
            prob += x[(i, j)] <= pct * y[j]

    revenue = pulp.lpSum(sell_price[j] * y[j] for j in range(3))
    material_cost = pulp.lpSum(raw_cost[i] * x[(i, j)] for i in range(3) for j in range(3))
    processing_cost = pulp.lpSum(proc_fee[j] * y[j] for j in range(3))
    fixed_setup_cost = pulp.lpSum(setup_cost[j] * z[j] for j in range(3))
    shared_wrapper_cost = params.get('BrandAB_SharedWrapper_Fee', 0.0) * shared_ab_wrapper

    prob += revenue - material_cost - processing_cost - fixed_setup_cost - shared_wrapper_cost

    prob.solve(pulp.GUROBI_CMD(msg=0))

    value = float(pulp.value(prob.objective))
    print(f"OBJECTIVE_VALUE: {value}")


if __name__ == '__main__':
    main()
