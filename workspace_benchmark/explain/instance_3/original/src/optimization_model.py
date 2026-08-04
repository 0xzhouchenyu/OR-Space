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

# Model
prob = LpProblem("FoldableTableProduction", LpMaximize)

# Decision variables
W = [LpVariable(f"W_{t}", lowBound=0, cat='Continuous') for t in range(T)]  # workforce
H = [LpVariable(f"H_{t}", lowBound=0, cat='Continuous') for t in range(T)]  # hired
F = [LpVariable(f"F_{t}", lowBound=0, cat='Continuous') for t in range(T)]  # fired
P = [LpVariable(f"P_{t}", lowBound=0, cat='Continuous') for t in range(T)]  # in-house production
OT_total = [LpVariable(f"OT_{t}", lowBound=0, cat='Continuous') for t in range(T)]  # total overtime hours
O = [LpVariable(f"O_{t}", lowBound=0, cat='Continuous') for t in range(T)]  # outsourced units
Inv = [LpVariable(f"Inv_{t}", lowBound=0, cat='Continuous') for t in range(T)]  # inventory
B = [LpVariable(f"B_{t}", lowBound=0, cat='Continuous') for t in range(T)]  # backorders

# Revenue: sales_price * units sold. Total demand fulfilled = total demand - ending backorders + starting backorders
# Net inventory: Inv[t] - B[t] = (prev_inv - prev_backorder) + P[t] + O[t] - demand[t]

# Constraints
for t in range(T):
    # Workforce balance
    if t == 0:
        prob += W[t] == W0 + H[t] - F[t]
    else:
        prob += W[t] == W[t-1] + H[t] - F[t]
    
    # Production limited by total labor hours (regular + overtime)
    prob += P[t] * lr <= W[t] * rh + OT_total[t]
    
    # Overtime limit
    prob += OT_total[t] <= W[t] * otl
    
    # Inventory balance: Inv[t] - B[t] = (Inv[t-1] - B[t-1]) + P[t] + O[t] - demand[t]
    prev_inv = I0 if t == 0 else Inv[t-1]
    prev_b = 0 if t == 0 else B[t-1]
    prob += Inv[t] - B[t] == prev_inv - prev_b + P[t] + O[t] - demand[t]

# Terminal conditions
prob += Inv[T-1] >= term_inv
prob += B[T-1] <= term_bo

# Objective: maximize net profit
# Revenue = sales_price * total units sold
# Total units sold = sum of demand (all demand eventually met since terminal backorders = 0)
total_demand = sum(demand[t] for t in range(T))
revenue = sp * total_demand

# Costs
material_cost = lpSum([rmc * P[t] for t in range(T)])
outsource_cost = lpSum([oc * O[t] for t in range(T)])
holding_cost = lpSum([hc * Inv[t] for t in range(T)])
backorder_cost_total = lpSum([bc * B[t] for t in range(T)])
regular_labor_cost = lpSum([rw * rh * W[t] for t in range(T)])
overtime_cost = lpSum([ow * OT_total[t] for t in range(T)])
hiring_cost_total = lpSum([hire_cost * H[t] for t in range(T)])
firing_cost_total = lpSum([fire_cost * F[t] for t in range(T)])

total_cost = (material_cost + outsource_cost + holding_cost + backorder_cost_total +
              regular_labor_cost + overtime_cost + hiring_cost_total + firing_cost_total)

prob += revenue - total_cost

# Solve
prob.solve(GUROBI_CMD(msg=0))

obj_val = value(prob.objective)
print(f"Status: {LpStatus[prob.status]}")

for t in range(T):
    print(f"Month {t+1}: W={value(W[t]):.0f}, H={value(H[t]):.0f}, F={value(F[t]):.0f}, "
          f"P={value(P[t]):.0f}, OT={value(OT_total[t]):.0f}, O={value(O[t]):.0f}, "
          f"Inv={value(Inv[t]):.0f}, B={value(B[t]):.0f}")

print(f"OBJECTIVE_VALUE: {obj_val}")