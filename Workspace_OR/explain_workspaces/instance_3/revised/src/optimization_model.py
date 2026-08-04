import os
import csv
from gurobi_pulp_compat import *

# Load data
base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# Load demand forecast
demand = {}
with open(os.path.join(base_dir, 'table_1.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        demand[i] = float(row['Demand_Forecast'])

T = len(demand)  # 6 months

# Load general parameters
params = {}
with open(os.path.join(base_dir, 'general_parameters.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        params[row['Parameter_Name']] = float(row['Value'])

W0 = int(params['initial_workforce'])
I0 = params['initial_inventory']
sp = params['sales_price']
rmc = params['raw_material_cost']
oc = params['outsourcing_cost']
hc = params['inventory_holding_cost']
bc = params['backorder_cost']
lr = params['labor_requirement']
rh = params['regular_labor_hours']
rw = params['regular_wage']
otl = params['overtime_hours_limit']
ow = params['overtime_wage']
hire_cost = params['hiring_cost']
fire_cost = params['firing_cost']
term_inv = params['terminal_inventory']
term_bo = params['terminal_backorders']
contract_min_units = params['contract_min_units']
contract_bigM = params['contract_bigM']

# Model
prob = LpProblem("FoldableTableProduction_Contract", LpMaximize)

# Decision variables
W = [LpVariable(f"W_{t}", lowBound=0, cat='Continuous') for t in range(T)]  # workforce
H = [LpVariable(f"H_{t}", lowBound=0, cat='Continuous') for t in range(T)]  # hired
F = [LpVariable(f"F_{t}", lowBound=0, cat='Continuous') for t in range(T)]  # fired
P = [LpVariable(f"P_{t}", lowBound=0, cat='Continuous') for t in range(T)]  # total in-house production
P_reg = [LpVariable(f"P_reg_{t}", lowBound=0, cat='Continuous') for t in range(T)]  # regular-time production
P_ot = [LpVariable(f"P_ot_{t}", lowBound=0, cat='Continuous') for t in range(T)]  # overtime production
OT_total = [LpVariable(f"OT_{t}", lowBound=0, cat='Continuous') for t in range(T)]  # total overtime hours
O = [LpVariable(f"O_{t}", lowBound=0, cat='Continuous') for t in range(T)]  # outsourced units
Inv = [LpVariable(f"Inv_{t}", lowBound=0, cat='Continuous') for t in range(T)]  # inventory
B = [LpVariable(f"B_{t}", lowBound=0, cat='Continuous') for t in range(T)]  # backorders

# Contract-related variables for April-June (t = 3,4,5)
C = [LpVariable(f"C_{t}", lowBound=0, cat='Continuous') for t in range(T)]  # will be constrained for t>=3
z = [LpVariable(f"z_{t}", lowBound=0, upBound=1, cat='Binary') for t in range(T)]

# Constraints
for t in range(T):
    # Workforce balance
    if t == 0:
        prob += W[t] == W0 + H[t] - F[t]
    else:
        prob += W[t] == W[t-1] + H[t] - F[t]

    # Regular-time capacity
    prob += P_reg[t] * lr <= W[t] * rh

    # Overtime production and hours linking
    prob += P_ot[t] * lr == OT_total[t]

    # Overtime limit
    prob += OT_total[t] <= W[t] * otl

    # Total production decomposition
    prob += P[t] == P_reg[t] + P_ot[t]

    # Inventory balance
    prev_inv = I0 if t == 0 else Inv[t-1]
    prev_b = 0 if t == 0 else B[t-1]
    prob += Inv[t] - B[t] == prev_inv - prev_b + P[t] + O[t] - demand[t]

# Contract constraints for April-June (t=3,4,5)
for t in range(3, T):
    # net demand = current demand + previous backorders
    net_demand_expr = demand[t] + B[t-1]

    # C_t bounded by regular production and net demand
    prob += C[t] <= P_reg[t]
    prob += C[t] <= net_demand_expr

    # minimum contract requirement
    prob += C[t] >= contract_min_units

    # big-M linkage with binary z_t
    prob += C[t] <= contract_bigM * z[t]

# For months before contract (t=0,1,2), force C[t] = 0 and z[t] = 0
for t in range(3):
    prob += C[t] == 0
    prob += z[t] == 0

# Terminal conditions
prob += Inv[T-1] >= term_inv
prob += B[T-1] <= term_bo

# Objective: maximize net profit
# Revenue: sales_price * total demand (all demand is eventually met because final backorders are zero)
total_demand = sum(demand[t] for t in range(T))
revenue = sp * total_demand

# Costs
material_cost = lpSum(rmc * P[t] for t in range(T))
outsource_cost = lpSum(oc * O[t] for t in range(T))
holding_cost = lpSum(hc * Inv[t] for t in range(T))
backorder_cost_total = lpSum(bc * B[t] for t in range(T))
regular_labor_cost = lpSum(rw * rh * W[t] for t in range(T))
overtime_cost = lpSum(ow * OT_total[t] for t in range(T))
hiring_cost_total = lpSum(hire_cost * H[t] for t in range(T))
firing_cost_total = lpSum(fire_cost * F[t] for t in range(T))

total_cost = (material_cost + outsource_cost + holding_cost + backorder_cost_total +
              regular_labor_cost + overtime_cost + hiring_cost_total + firing_cost_total)

prob += revenue - total_cost

# Solve
prob.solve(GUROBI_CMD(msg=0))

obj_val = value(prob.objective)
print(f"OBJECTIVE_STATUS: {LpStatus[prob.status]}")
print(f"OBJECTIVE_VALUE: {obj_val}")
