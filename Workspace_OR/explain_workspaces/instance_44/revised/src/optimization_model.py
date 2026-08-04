import os
import csv
from gurobi_pulp_compat import *

# Load data directory
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
q = {k: params[f'q_{k}'] for k in range(1, p+1)}  # max total transshipment capacity
qexp = {k: params[f'qexp_{k}'] for k in range(1, p+1)}  # max express capacity
alpha = {j: params[f'alpha_{j}'] for j in range(1, n+1)}  # min express fraction

# Indicator parameters for big-M constraints
eps = params['eps']
M_big = params['M']

# Load transportation costs from production to marshaling stations (regular and express)
cR_ik = {}
cE_ik = {}
with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        i = int(row['i'])
        k = int(row['k'])
        cR_ik[(i, k)] = float(row['cR_ik'])
        cE_ik[(i, k)] = float(row['cE_ik'])

# Load transportation costs from marshaling stations to demand points (regular and express)
cR_kj = {}
cE_kj = {}
with open(os.path.join(data_dir, 'table_2.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        k = int(row['k'])
        j = int(row['j'])
        cR_kj[(k, j)] = float(row['cR_kj'])
        cE_kj[(k, j)] = float(row['cE_kj'])

# Create the optimization model
prob = LpProblem("Transportation_Problem_Mode_Split_Diversification", LpMinimize)

# Decision variables
# xR_ik, xE_ik: regular and express flows from production i to station k
xR = {}
xE = {}
for i in range(1, m+1):
    for k in range(1, p+1):
        xR[(i, k)] = LpVariable(f"xR_{i}_{k}", lowBound=0, cat='Continuous')
        xE[(i, k)] = LpVariable(f"xE_{i}_{k}", lowBound=0, cat='Continuous')

# yR_kj, yE_kj: regular and express flows from station k to demand j
yR = {}
yE = {}
for k in range(1, p+1):
    for j in range(1, n+1):
        yR[(k, j)] = LpVariable(f"yR_{k}_{j}", lowBound=0, cat='Continuous')
        yE[(k, j)] = LpVariable(f"yE_{k}_{j}", lowBound=0, cat='Continuous')

# z_k: binary variable indicating whether marshaling station k is used
z = {k: LpVariable(f"z_{k}", cat='Binary') for k in range(1, p+1)}

# u_jk: binary indicator that station k sends positive express flow to demand j
u = {}
# w_kj: binary indicator that station k is counted as an express source for demand j
w = {}
for k in range(1, p+1):
    for j in range(1, n+1):
        u[(j, k)] = LpVariable(f"u_{j}_{k}", cat='Binary')
        w[(k, j)] = LpVariable(f"w_{k}_{j}", cat='Binary')

# v: binary indicator that at least two stations are open
v = LpVariable("v", cat='Binary')

# Objective: minimize total cost (regular + express + fixed station costs)
prob += (
    lpSum(cR_ik[(i, k)] * xR[(i, k)] + cE_ik[(i, k)] * xE[(i, k)]
          for i in range(1, m+1) for k in range(1, p+1))
    + lpSum(cR_kj[(k, j)] * yR[(k, j)] + cE_kj[(k, j)] * yE[(k, j)]
            for k in range(1, p+1) for j in range(1, n+1))
    + lpSum(f_cost[k] * z[k] for k in range(1, p+1))
)

# Constraints

# 1. Supply constraints at production points
total_supply = 0.0
for i in range(1, m+1):
    prob += lpSum(xR[(i, k)] + xE[(i, k)] for k in range(1, p+1)) <= a[i], f"Supply_{i}"
    total_supply += a[i]

# 2. Demand fulfillment at demand points (exact)
for j in range(1, n+1):
    prob += lpSum(yR[(k, j)] + yE[(k, j)] for k in range(1, p+1)) == b[j], f"Demand_{j}"

# 3. Flow conservation at stations per mode
for k in range(1, p+1):
    prob += lpSum(xR[(i, k)] for i in range(1, m+1)) == lpSum(yR[(k, j)] for j in range(1, n+1)), f"FlowBalance_R_{k}"
    prob += lpSum(xE[(i, k)] for i in range(1, m+1)) == lpSum(yE[(k, j)] for j in range(1, n+1)), f"FlowBalance_E_{k}"

# 4. Station total capacity constraints (linked with z_k)
for k in range(1, p+1):
    prob += lpSum(xR[(i, k)] + xE[(i, k)] for i in range(1, m+1)) <= q[k] * z[k], f"CapacityTotal_{k}"

# 5. Station express-capacity constraints
for k in range(1, p+1):
    prob += lpSum(xE[(i, k)] for i in range(1, m+1)) <= qexp[k] * z[k], f"CapacityExpress_{k}"

# 6. Express-share constraints at demands
for j in range(1, n+1):
    prob += lpSum(yE[(k, j)] for k in range(1, p+1)) >= alpha[j] * b[j], f"ExpressShare_{j}"

# 7. Indicator consistency constraints for express sourcing (u)
# yE_kj >= eps * u_jk and yE_kj <= M * u_jk
for k in range(1, p+1):
    for j in range(1, n+1):
        prob += yE[(k, j)] >= eps * u[(j, k)], f"MinExpress_{k}_{j}"
        prob += yE[(k, j)] <= M_big * u[(j, k)], f"MaxExpress_{k}_{j}"

# 8. Link w_kj to station usage and express sourcing
for k in range(1, p+1):
    for j in range(1, n+1):
        prob += w[(k, j)] <= u[(j, k)], f"W_leq_U_{k}_{j}"
        prob += w[(k, j)] <= z[k], f"W_leq_Z_{k}_{j}"

# 9. Open-coverage indicator v
# Let S = sum_k z_k
S = lpSum(z[k] for k in range(1, p+1))
# For p=2: v <= S - 1 and S - v >= 1
prob += v <= S - 1, "v_upper"
prob += S - v >= 1, "v_lower"

# 10. Diversification requirement per demand: sum_k w_kj >= 2 * v
for j in range(1, n+1):
    prob += lpSum(w[(k, j)] for k in range(1, p+1)) >= 2 * v, f"Diversification_{j}"

# Solve the model
prob.solve(GUROBI_CMD(msg=0))

obj_val = value(prob.objective)
print(f"OBJECTIVE_VALUE: {obj_val}")
