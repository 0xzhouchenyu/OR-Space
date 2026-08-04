import os
import csv
from gurobi_pulp_compat import *

data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

goods = {}
with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        goods[row['Goods_Type']] = {
            'quantity': float(row['Quantity']),
            'weight': float(row['Weight_per_Unit'])
        }

params = {}
with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        params[row['Parameter_Name']] = float(row['Value'])

max_cap = params['max_container_capacity']
min_load = params['min_container_load']
min_d_per_container = int(params['min_d_goods_per_container'])
min_c_per_a = int(params['min_c_per_a'])

goods_types = list(goods.keys())
quantities = {g: goods[g]['quantity'] for g in goods_types}
weights = {g: goods[g]['weight'] for g in goods_types}

max_containers = 15
N = range(max_containers)

prob = LpProblem("ContainerMinimization", LpMinimize)

x = {g: {j: LpVariable(f"x_{g}_{j}", lowBound=0, cat='Integer') for j in N} for g in goods_types}
y = {j: LpVariable(f"y_{j}", cat='Binary') for j in N}
has_E = {j: LpVariable(f"has_E_{j}", cat='Binary') for j in N}
z = {j: LpVariable(f"z_{j}", cat='Binary') for j in N}

prob += lpSum(y[j] for j in N)

for g in goods_types:
    prob += lpSum(x[g][j] for j in N) == quantities[g], f"demand_{g}"

M_E = quantities['E']
M_A = quantities['A']

for j in N:
    prob += x['E'][j] <= M_E * has_E[j], f"E_indicator_{j}"
    prob += lpSum(weights[g] * x[g][j] for g in goods_types) <= max_cap * y[j] - 15 * has_E[j], f"max_cap_{j}"
    prob += lpSum(weights[g] * x[g][j] for g in goods_types) >= min_load * y[j], f"min_load_{j}"
    prob += x['D'][j] >= min_d_per_container * y[j], f"min_D_{j}"
    prob += x['A'][j] <= M_A * z[j], f"A_indicator_{j}"
    prob += x['C'][j] >= min_c_per_a * z[j], f"C_if_A_{j}"

for j in range(len(N) - 1):
    prob += y[j] >= y[j+1], f"symmetry_{j}"

prob.solve(GUROBI_CMD(msg=0, timeLimit=120))

obj_val = value(prob.objective)
print(f"OBJECTIVE_VALUE: {obj_val}")