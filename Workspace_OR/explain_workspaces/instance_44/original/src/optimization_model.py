import os
import csv
from gurobi_pulp_compat import *

# Load data
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# Load general parameters
params = {}
with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        params[row['Parameter_Name']] = float(row['Value'])

m = int(params['m'])  # production points
n = int(params['n'])  # demand points
p = int(params['p'])  # marshaling stations

a = {i: params[f'a_{i}'] for i in range(1, m+1)}  # production capacities
b = {j: params[f'b_{j}'] for j in range(1, n+1)}  # demands
f_cost = {k: params[f'f_{k}'] for k in range(1, p+1)}  # fixed costs
q = {k: params[f'q_{k}'] for k in range(1, p+1)}  # max transshipment capacity

# Load transportation costs from production to marshaling stations
c_ik = {}
with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        i = int(row['i'])
        k = int(row['k'])
        c_ik[(i, k)] = float(row['c_ik'])

# Load transportation costs from marshaling stations to demand points
c_kj = {}
with open(os.path.join(data_dir, 'table_2.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        k = int(row['k'])
        j = int(row['j'])
        c_kj[(k, j)] = float(row["c'_kj"])

# Create the optimization model
prob = LpProblem("Transportation_Problem", LpMinimize)

# Decision variables
# x_ik: amount shipped from production point i to marshaling station k
x = {}
for i in range(1, m+1):
    for k in range(1, p+1):
        x[(i, k)] = LpVariable(f"x_{i}_{k}", lowBound=0, cat='Continuous')

# y_kj: amount shipped from marshaling station k to demand point j
y = {}
for k in range(1, p+1):
    for j in range(1, n+1):
        y[(k, j)] = LpVariable(f"y_{k}_{j}", lowBound=0, cat='Continuous')

# z_k: binary variable indicating whether marshaling station k is used
z = {}
for k in range(1, p+1):
    z[k] = LpVariable(f"z_{k}", cat='Binary')

# Objective: minimize total transportation cost + fixed costs
prob += (
    lpSum(c_ik[(i, k)] * x[(i, k)] for i in range(1, m+1) for k in range(1, p+1)) +
    lpSum(c_kj[(k, j)] * y[(k, j)] for k in range(1, p+1) for j in range(1, n+1)) +
    lpSum(f_cost[k] * z[k] for k in range(1, p+1))
)

# Constraints

# 1. Supply constraints: total shipped from production point i <= a_i
for i in range(1, m+1):
    prob += lpSum(x[(i, k)] for k in range(1, p+1)) <= a[i], f"Supply_{i}"

# 2. Demand constraints: total received at demand point j >= b_j
for j in range(1, n+1):
    prob += lpSum(y[(k, j)] for k in range(1, p+1)) >= b[j], f"Demand_{j}"

# 3. Flow conservation at marshaling stations
for k in range(1, p+1):
    prob += lpSum(x[(i, k)] for i in range(1, m+1)) == lpSum(y[(k, j)] for j in range(1, n+1)), f"FlowBalance_{k}"

# 4. Capacity constraints at marshaling stations (linked with z_k)
for k in range(1, p+1):
    prob += lpSum(x[(i, k)] for i in range(1, m+1)) <= q[k] * z[k], f"Capacity_{k}"

# Solve
prob.solve(GUROBI_CMD(msg=0))

# Print solution details
for k in range(1, p+1):
    print(f"Station {k} used: {z[k].varValue}")
for i in range(1, m+1):
    for k in range(1, p+1):
        if x[(i,k)].varValue > 0:
            print(f"x[{i},{k}] = {x[(i,k)].varValue}")
for k in range(1, p+1):
    for j in range(1, n+1):
        if y[(k,j)].varValue > 0:
            print(f"y[{k},{j}] = {y[(k,j)].varValue}")

obj_val = value(prob.objective)
print(f"OBJECTIVE_VALUE: {obj_val}")