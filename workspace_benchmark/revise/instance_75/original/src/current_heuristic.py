import os
import sys
from utils import load_parameters
import gurobi_pulp_compat as pulp

# Load data
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
params = load_parameters(os.path.join(data_dir, 'general_parameters.csv'))

# Extract parameters
a_p1 = params['product_a_process_1_time']
a_p2 = params['product_a_process_2_time']
b_p1 = params['product_b_process_1_time']
b_p2 = params['product_b_process_2_time']
T1 = params['available_time_process_1']
T2 = params['available_time_process_2']
c_per_b = params['byproduct_c_per_unit_b']
max_c_sales = params['max_byproduct_c_sales']
disposal_cost = params['disposal_cost_per_unit_c']
profit_a = params['profit_per_unit_a']
profit_b = params['profit_per_unit_b']
profit_c = params['profit_per_unit_c']

# Create the LP problem
prob = pulp.LpProblem("MaxProfit", pulp.LpMaximize)

# Decision variables
xA = pulp.LpVariable("xA", lowBound=0)  # units of product A
xB = pulp.LpVariable("xB", lowBound=0)  # units of product B
cSold = pulp.LpVariable("cSold", lowBound=0)  # units of by-product C sold
cDisposed = pulp.LpVariable("cDisposed", lowBound=0)  # units of by-product C disposed

# Objective: maximize total profit
# Profit from A + Profit from B + Profit from selling C - Cost of disposing C
prob += profit_a * xA + profit_b * xB + profit_c * cSold - disposal_cost * cDisposed, "TotalProfit"

# Constraints
# Process 1 time constraint
prob += a_p1 * xA + b_p1 * xB <= T1, "Process1Time"

# Process 2 time constraint
prob += a_p2 * xA + b_p2 * xB <= T2, "Process2Time"

# By-product C balance: total C produced = C sold + C disposed
prob += cSold + cDisposed == c_per_b * xB, "ByproductBalance"

# Maximum C that can be sold
prob += cSold <= max_c_sales, "MaxCSales"

# Solve
prob.solve(pulp.GUROBI_CMD(msg=0))

# Output results
print(f"Status: {pulp.LpStatus[prob.status]}")
print(f"xA = {pulp.value(xA)}")
print(f"xB = {pulp.value(xB)}")
print(f"cSold = {pulp.value(cSold)}")
print(f"cDisposed = {pulp.value(cDisposed)}")

obj_val = pulp.value(prob.objective)
print(f"OBJECTIVE_VALUE: {obj_val}")