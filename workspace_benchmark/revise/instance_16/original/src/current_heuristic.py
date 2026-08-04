import os
import sys
from gurobi_pulp_compat import *

# Add parent directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from utils import load_monthly_data, load_general_parameters

# Load data
data_dir = os.path.join(script_dir, '..', 'data')
months, purchasing_prices, selling_prices = load_monthly_data(os.path.join(data_dir, 'table_1.csv'))
params = load_general_parameters(os.path.join(data_dir, 'general_parameters.csv'))

warehouse_capacity = params['warehouse_capacity']
initial_stock = params['initial_stock']

# Create the LP problem
prob = LpProblem("Maximize_Profit", LpMaximize)

# Decision variables
# x[m] = units purchased at the beginning of month m
# s[m] = units sold during month m
x = {m: LpVariable(f"purchase_{m}", lowBound=0, cat='Continuous') for m in months}
s = {m: LpVariable(f"sell_{m}", lowBound=0, cat='Continuous') for m in months}

# Inventory at the end of each month (auxiliary variables)
# inv[m] = inventory at end of month m
inv = {m: LpVariable(f"inventory_{m}", lowBound=0, cat='Continuous') for m in months}

# Objective: maximize total profit = sum of (selling revenue - purchasing cost)
prob += lpSum([selling_prices[m] * s[m] - purchasing_prices[m] * x[m] for m in months])

# Constraints
for m in months:
    # Inventory balance: inv[m] = inv[m-1] + x[m] - s[m]
    if m == months[0]:
        prev_inv = initial_stock
    else:
        prev_inv = inv[m - 1]
    
    prob += inv[m] == prev_inv + x[m] - s[m], f"inventory_balance_{m}"
    
    # Warehouse capacity constraint: inventory after purchasing (before selling) <= warehouse_capacity
    # At the beginning of month m, we purchase x[m], so stock becomes prev_inv + x[m]
    # This must not exceed warehouse capacity
    prob += prev_inv + x[m] <= warehouse_capacity, f"warehouse_after_purchase_{m}"
    
    # End-of-month inventory also cannot exceed warehouse capacity
    prob += inv[m] <= warehouse_capacity, f"warehouse_end_{m}"
    
    # Can't sell more than what's available (prev_inv + x[m])
    prob += s[m] <= prev_inv + x[m], f"sell_limit_{m}"

# Solve
prob.solve(GUROBI_CMD(msg=0))

# Print results
for m in months:
    print(f"Month {m}: Purchase = {value(x[m])}, Sell = {value(s[m])}, End Inventory = {value(inv[m])}")

obj_val = value(prob.objective)
print(f"OBJECTIVE_VALUE: {obj_val}")