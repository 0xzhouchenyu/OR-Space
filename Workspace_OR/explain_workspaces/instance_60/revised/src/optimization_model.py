import os
import re
import csv
import gurobi_pulp_compat as pulp
from utils import get_data_dir

def load_parameters(data_dir):
    params = {
        'num_customers': 7,
        'start_location': 1,
        'end_location': 1,
        'max_route_length_day': 1000.0,
        'route_cost_day': 20.0
    }
    gp_path = os.path.join(data_dir, 'general_parameters.csv')
    if not os.path.exists(gp_path):
        return params
    with open(gp_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['Parameter_Name']
            val = row['Value']
            if name == 'num_customers' and val != '':
                params['num_customers'] = int(val)
            elif name == 'start_location' and val != '':
                params['start_location'] = int(val)
            elif name == 'end_location' and val != '':
                params['end_location'] = int(val)
            elif name == 'max_route_length_day' and val != '':
                params['max_route_length_day'] = float(val)
            elif name == 'route_cost_day' and val != '':
                params['route_cost_day'] = float(val)
    return params

def load_distance_matrix(data_dir, num_customers):
    D = [[0.0] * num_customers for _ in range(num_customers)]
    table_path = os.path.join(data_dir, 'table_1.csv')
    if not os.path.exists(table_path):
        return D
    with open(table_path, 'r') as f:
        lines = f.readlines()
        for line in lines[1:]:
            nums = re.findall(r'\d+', line)
            if not nums:
                continue
            row_idx = int(nums[0]) - 1
            for j, val in enumerate(nums[1:]):
                col_idx = row_idx + 1 + j
                if col_idx < num_customers:
                    D[row_idx][col_idx] = float(val)
                    D[col_idx][row_idx] = float(val)
    return D

def solve():
    data_dir = get_data_dir()
    params = load_parameters(data_dir)
    num_customers = params['num_customers']
    max_route_length_day = params['max_route_length_day']
    route_cost_day = params['route_cost_day']

    D = load_distance_matrix(data_dir, num_customers)

    days = [1, 2]
    locations = list(range(num_customers))  # 0..num_customers-1, where 0 is depot (location 1)
    customers = [i for i in locations if i != 0]

    prob = pulp.LpProblem('TwoDay_TSP_Assignment', pulp.LpMinimize)

    x = pulp.LpVariable.dicts(
        'x',
        ((i, j, d) for i in locations for j in locations for d in days if i != j),
        lowBound=0,
        upBound=1,
        cat='Binary'
    )

    u = pulp.LpVariable.dicts(
        'u',
        ((i, d) for i in customers for d in days),
        lowBound=1,
        upBound=num_customers - 1,
        cat='Continuous'
    )

    y = pulp.LpVariable.dicts(
        'y',
        ((i, d) for i in customers for d in days),
        lowBound=0,
        upBound=1,
        cat='Binary'
    )

    z = pulp.LpVariable.dicts(
        'z',
        (d for d in days),
        lowBound=0,
        upBound=1,
        cat='Binary'
    )

    prob += (
        pulp.lpSum(D[i][j] * x[i, j, d] for i in locations for j in locations for d in days if i != j)
        + pulp.lpSum(route_cost_day * z[d] for d in days)
    )

    for i in customers:
        prob += pulp.lpSum(y[i, d] for d in days) == 1, f'assign_once_{i}'

    for d in days:
        for i in customers:
            prob += pulp.lpSum(x[i, j, d] for j in locations if j != i) == y[i, d], f'cust_out_{i}_{d}'
            prob += pulp.lpSum(x[j, i, d] for j in locations if j != i) == y[i, d], f'cust_in_{i}_{d}'

    for d in days:
        prob += pulp.lpSum(x[0, j, d] for j in customers) == z[d], f'dep_out_{d}'
        prob += pulp.lpSum(x[j, 0, d] for j in customers) == z[d], f'dep_in_{d}'

    for d in days:
        for i in customers:
            prob += y[i, d] <= z[d], f'assign_day_active_{i}_{d}'

    for d in days:
        for i in customers:
            for j in customers:
                if i != j:
                    prob += (
                        u[i, d] - u[j, d] + (num_customers - 1) * x[i, j, d]
                        <= num_customers - 2
                    ), f'mtz_{i}_{j}_{d}'

    for d in days:
        prob += (
            pulp.lpSum(D[i][j] * x[i, j, d] for i in locations for j in locations if i != j)
            <= max_route_length_day
        ), f'max_len_{d}'

    solver = pulp.GUROBI_CMD(msg=False)
    prob.solve(solver)

    obj_val = float(pulp.value(prob.objective))
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == '__main__':
    solve()
