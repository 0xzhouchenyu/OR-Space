import os
import re
import csv
import gurobi_pulp_compat as pulp
from utils import get_data_dir

def solve():
    data_dir = get_data_dir()
    
    num_customers = 7
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Parameter_Name'] == 'num_customers':
                num_customers = int(row['Value'])

    D = [[0] * num_customers for _ in range(num_customers)]
    with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
        lines = f.readlines()
        for line in lines[1:]:
            nums = re.findall(r'\d+', line)
            if not nums:
                continue
            row_idx = int(nums[0]) - 1
            for j, val in enumerate(nums[1:]):
                col_idx = row_idx + 1 + j
                if col_idx < num_customers:
                    D[row_idx][col_idx] = int(val)
                    D[col_idx][row_idx] = int(val)

    prob = pulp.LpProblem("TSP", pulp.LpMinimize)

    x = pulp.LpVariable.dicts("x", ((i, j) for i in range(num_customers) for j in range(num_customers) if i != j), cat='Binary')
    u = pulp.LpVariable.dicts("u", (i for i in range(1, num_customers)), lowBound=1, upBound=num_customers-1, cat='Continuous')

    prob += pulp.lpSum(D[i][j] * x[i, j] for i in range(num_customers) for j in range(num_customers) if i != j)

    for i in range(num_customers):
        prob += pulp.lpSum(x[i, j] for j in range(num_customers) if i != j) == 1
        prob += pulp.lpSum(x[j, i] for j in range(num_customers) if i != j) == 1

    for i in range(1, num_customers):
        for j in range(1, num_customers):
            if i != j:
                prob += u[i] - u[j] + (num_customers - 1) * x[i, j] <= num_customers - 2

    prob.solve(pulp.GUROBI_CMD(msg=False))

    print(f"OBJECTIVE_VALUE: {float(pulp.value(prob.objective))}")

if __name__ == "__main__":
    solve()