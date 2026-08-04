import os
import sys
from gurobi_pulp_compat import *
from utils import load_goods_data, load_parameters

# Load data
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
goods = load_goods_data(os.path.join(data_dir, 'table_1.csv'))
params = load_parameters(os.path.join(data_dir, 'general_parameters.csv'))

max_cap = params['max_container_capacity']
min_load = params['min_container_load']
min_d_per_container = int(params['min_d_goods_per_container'])
min_c_per_a = int(params['min_c_per_a'])

goods_types = list(goods.keys())
quantities = {g: goods[g]['quantity'] for g in goods_types}
weights = {g: goods[g]['weight'] for g in goods_types}

# Upper bound on number of containers
# We need at least enough containers to supply 12 D goods each
# D has 90 units, so max containers from D constraint: 90/12 = 7.5 -> 7 containers (with 12 each = 84, but we have 90)
# Actually we need ceil(90/12) isn't right - we need ALL D distributed with min 12 per container
# Max containers possible: floor(90/12) = 7 (7*12=84, remaining 6 must go somewhere in those 7)
max_containers = 15  # generous upper bound

N = range(max_containers)

prob = LpProblem("ContainerMinimization", LpMinimize)

# Decision variables
# x[g][j] = number of units of goods type g in container j
x = {g: {j: LpVariable(f"x_{g}_{j}", lowBound=0, cat='Integer') for j in N} for g in goods_types}
# y[j] = 1 if container j is used
y = {j: LpVariable(f"y_{j}", cat='Binary') for j in N}

# Objective: minimize number of containers
prob += lpSum(y[j] for j in N)

# All goods must be transported
for g in goods_types:
    prob += lpSum(x[g][j] for j in N) == quantities[g], f"demand_{g}"

# Container capacity constraint
for j in N:
    prob += lpSum(weights[g] * x[g][j] for g in goods_types) <= max_cap * y[j], f"max_cap_{j}"

# Minimum load constraint
for j in N:
    prob += lpSum(weights[g] * x[g][j] for g in goods_types) >= min_load * y[j], f"min_load_{j}"

# Minimum D goods per container (if container is used)
for j in N:
    prob += x['D'][j] >= min_d_per_container * y[j], f"min_D_{j}"

# If A goods are loaded, at least 1 C good must be loaded
# x['A'][j] <= M * z[j], x['C'][j] >= z[j], where z[j] indicates A is present
M_A = quantities['A']
z = {j: LpVariable(f"z_{j}", cat='Binary') for j in N}
for j in N:
    prob += x['A'][j] <= M_A * z[j], f"A_indicator_{j}"
    prob += x['C'][j] >= min_c_per_a * z[j], f"C_if_A_{j}"

# Symmetry breaking
for j in range(len(N) - 1):
    prob += y[j] >= y[j+1], f"symmetry_{j}"

# Solve
prob.solve(GUROBI_CMD(msg=1, timeLimit=120))

obj_val = value(prob.objective)
print(f"Status: {LpStatus[prob.status]}")
for j in N:
    if value(y[j]) > 0.5:
        contents = {g: int(value(x[g][j])) for g in goods_types if value(x[g][j]) > 0.5}
        total_w = sum(weights[g] * value(x[g][j]) for g in goods_types)
        print(f"  Container {j}: {contents}, weight={total_w:.1f}")

print(f"OBJECTIVE_VALUE: {obj_val}")