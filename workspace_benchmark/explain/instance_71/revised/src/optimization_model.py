import os
import csv
from itertools import product
from gurobi_pulp_compat import LpProblem, LpMinimize, LpVariable, lpSum, LpBinary, LpStatusOptimal, value, GUROBI_CMD


def read_data():
    base = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base, '..', 'data')

    # Read table_1.csv
    with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    n = len(rows)

    d = [[0.0 for _ in range(n)] for _ in range(n)]
    c = [[0.0 for _ in range(n)] for _ in range(n)]

    for i, row in enumerate(rows):
        for j in range(n):
            d[i][j] = float(row[f'Transportation_volume_to_Location_{j+1}'])
            c[i][j] = float(row[f'Transportation_cost_to_Location_{j+1}'])

    # Read general_parameters.csv for premium parameters
    premium_cost_multiplier = 1.5
    min_premium_share = 0.4
    try:
        with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row['Parameter_Name']
                if name == 'premium_cost_multiplier':
                    premium_cost_multiplier = float(row['Value'])
                elif name == 'min_premium_share':
                    min_premium_share = float(row['Value'])
    except FileNotFoundError:
        pass

    return n, d, c, premium_cost_multiplier, min_premium_share


def build_and_solve():
    n, d, c, premium_cost_multiplier, min_premium_share = read_data()

    factories = list(range(n))
    locations = list(range(n))

    # outbound volume per factory
    outbound = {i: sum(d[i][j] for j in locations) for i in factories}

    # Standard unit cost c_std_ip is derived as average unit cost from location p to all destinations,
    # scaled to maintain the original relative cost structure. Here, for simplicity, we define
    # c_std_ip = sum_j d[i][j] * c[p][j] / outbound[i] when outbound[i] > 0, else 0.
    c_std = {}
    for i in factories:
        for p in locations:
            if outbound[i] > 0:
                num = sum(d[i][j] * c[p][j] for j in locations)
                c_std[(i, p)] = num / outbound[i]
            else:
                c_std[(i, p)] = 0.0

    c_prem = {(i, p): premium_cost_multiplier * c_std[(i, p)] for i in factories for p in locations}

    # Model
    model = LpProblem("FactoryLocationAssignmentWithModes", LpMinimize)

    # Decision variables
    x = LpVariable.dicts("x", (factories, locations), lowBound=0, upBound=1, cat=LpBinary)
    y = LpVariable.dicts("y", (factories, locations), lowBound=0, upBound=1, cat=LpBinary)
    v_std = LpVariable.dicts("v_std", (factories, locations), lowBound=0)
    v_prem = LpVariable.dicts("v_prem", (factories, locations), lowBound=0)

    # Objective: minimize total cost
    model += lpSum(
        c_std[(i, p)] * v_std[i][p] + c_prem[(i, p)] * v_prem[i][p]
        for i, p in product(factories, locations)
    )

    # 1) Each factory assigned to exactly one location
    for i in factories:
        model += lpSum(x[i][p] for p in locations) == 1, f"assign_factory_{i}"

    # 2) Each location hosts at most one factory
    for p in locations:
        model += lpSum(x[i][p] for i in factories) <= 1, f"location_capacity_{p}"

    # 3) Volume balance for each factory: split outbound volume into std + prem at (exactly) one location
    for i in factories:
        model += lpSum(v_std[i][p] + v_prem[i][p] for p in locations) == outbound[i], f"volume_balance_{i}"

    # 4) Volume only at assigned location
    for i, p in product(factories, locations):
        M_i = outbound[i]
        model += v_std[i][p] <= M_i * x[i][p], f"std_only_if_assigned_{i}_{p}"
        model += v_prem[i][p] <= M_i * x[i][p], f"prem_only_if_assigned_{i}_{p}"

    # 5) Premium volume only if premium is selected
    for i, p in product(factories, locations):
        M_i = outbound[i]
        model += v_prem[i][p] <= M_i * y[i][p], f"prem_only_if_premium_{i}_{p}"

    # 6) Minimum premium share when premium selected
    for i, p in product(factories, locations):
        M_i = outbound[i]
        model += v_prem[i][p] >= min_premium_share * M_i * y[i][p], f"min_prem_share_{i}_{p}"

    # 7) Premium only at assigned location
    for i, p in product(factories, locations):
        model += y[i][p] <= x[i][p], f"premium_only_if_assigned_{i}_{p}"

    # Solve
    solver = GUROBI_CMD(msg=False)
    status = model.solve(solver)

    if status != LpStatusOptimal:
        raise RuntimeError("Solver did not find optimal solution")

    obj_value = value(model.objective)
    print(f"OBJECTIVE_VALUE: {obj_value}")


if __name__ == "__main__":
    build_and_solve()
