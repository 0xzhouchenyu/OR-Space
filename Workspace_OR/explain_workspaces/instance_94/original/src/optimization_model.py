import os
import csv
from gurobi_pulp_compat import *

# Load parameters
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

params = {}
with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        params[row['Parameter_Name'].strip()] = float(row['Value'].strip())

# Extract parameters
min_A_I = params['min_proportion_crude_A_type_I'] / 100.0  # 0.50
min_A_II = params['min_proportion_crude_A_type_II'] / 100.0  # 0.60
price_I = params['selling_price_type_I']  # 4800
price_II = params['selling_price_type_II']  # 5600
inv_A = params['inventory_crude_A']  # 500
inv_B = params['inventory_crude_B']  # 1000
max_purchase_A = params['max_purchase_crude_A']  # 1500
cost_tier1 = params['market_price_crude_A_tier_1']  # 10000
cost_tier2 = params['market_price_crude_A_tier_2']  # 8000
cost_tier3 = params['market_price_crude_A_tier_3']  # 6000

# Decision variables
prob = LpProblem("Oil_Blending", LpMaximize)

# Amount of crude A used in gasoline I and II
a1 = LpVariable("crude_A_in_I", lowBound=0)  # crude A -> gasoline I
a2 = LpVariable("crude_A_in_II", lowBound=0)  # crude A -> gasoline II
b1 = LpVariable("crude_B_in_I", lowBound=0)  # crude B -> gasoline I
b2 = LpVariable("crude_B_in_II", lowBound=0)  # crude B -> gasoline II

# Tiered purchase variables for crude A
p1 = LpVariable("purchase_tier1", lowBound=0, upBound=500)   # first 500t
p2 = LpVariable("purchase_tier2", lowBound=0, upBound=500)   # next 500t
p3 = LpVariable("purchase_tier3", lowBound=0, upBound=500)   # last 500t

# Binary variables to enforce tiered ordering
y1 = LpVariable("y1", cat='Binary')  # 1 if tier1 is fully used
y2 = LpVariable("y2", cat='Binary')  # 1 if tier2 is fully used

# Tiered ordering constraints
prob += p1 <= 500
prob += p2 <= 500 * y1
prob += p3 <= 500 * y2
prob += p1 >= 500 * y1
prob += p2 >= 500 * y2

# Total crude A available = inventory + purchased
total_A_purchased = p1 + p2 + p3
prob += a1 + a2 <= inv_A + total_A_purchased  # crude A supply
prob += b1 + b2 <= inv_B  # crude B supply

# Blending constraints (minimum proportion of crude A)
# For gasoline I: a1 / (a1 + b1) >= 0.5 => a1 >= 0.5*(a1+b1) => a1 - b1 >= 0
prob += a1 >= min_A_I * (a1 + b1)
# For gasoline II: a2 / (a2 + b2) >= 0.6
prob += a2 >= min_A_II * (a2 + b2)

# Revenue - Cost
revenue = price_I * (a1 + b1) + price_II * (a2 + b2)
cost = cost_tier1 * p1 + cost_tier2 * p2 + cost_tier3 * p3

prob += revenue - cost

prob.solve(GUROBI_CMD(msg=0))

obj_val = value(prob.objective)
print(f"Status: {LpStatus[prob.status]}")
print(f"Purchase tier1: {value(p1)}, tier2: {value(p2)}, tier3: {value(p3)}")
print(f"A in I: {value(a1)}, B in I: {value(b1)}")
print(f"A in II: {value(a2)}, B in II: {value(b2)}")
print(f"OBJECTIVE_VALUE: {obj_val}")