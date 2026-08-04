import os
import csv
from gurobi_pulp_compat import *

# Load data
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

months = []
purchasing_prices = {}
selling_prices = {}
with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        m = int(row['Month'])
        months.append(m)
        purchasing_prices[m] = float(row['Purchasing_Price_Yuan'])
        selling_prices[m] = float(row['Selling_Price_Yuan'])

params = {}
with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        params[row['Parameter_Name']] = float(row['Value'])

warehouse_capacity = params['warehouse_capacity']
initial_stock = params['initial_stock']
fixed_ordering_cost = params['fixed_ordering_cost']
month2_bulk_receiving_threshold = params['month2_bulk_receiving_threshold']
month2_bulk_receiving_fee = params['month2_bulk_receiving_fee']

# Create the LP problem
prob = LpProblem("Maximize_Profit", LpMaximize)

# Decision variables
x = {m: LpVariable(f"purchase_{m}", lowBound=0, cat='Continuous') for m in months}
s = {m: LpVariable(f"sell_{m}", lowBound=0, cat='Continuous') for m in months}
y = {m: LpVariable(f"purchase_flag_{m}", cat='Binary') for m in months}
inv = {m: LpVariable(f"inventory_{m}", lowBound=0, cat='Continuous') for m in months}
month2_bulk = LpVariable('month2_bulk_receiving', cat='Binary')

# Objective: maximize total profit = sum of (selling revenue - purchasing cost - fixed ordering cost)
prob += lpSum([selling_prices[m] * s[m] - purchasing_prices[m] * x[m] - fixed_ordering_cost * y[m] for m in months]) - month2_bulk_receiving_fee * month2_bulk

# Constraints
for m in months:
    if m == months[0]:
        prev_inv = initial_stock
    else:
        prev_inv = inv[m - 1]
    
    # Inventory balance
    prob += inv[m] == prev_inv + x[m] - s[m], f"inventory_balance_{m}"
    
    # Warehouse capacity constraint before selling
    prob += prev_inv + x[m] <= warehouse_capacity, f"warehouse_after_purchase_{m}"
    
    # Warehouse capacity constraint at end of month
    prob += inv[m] <= warehouse_capacity, f"warehouse_end_{m}"
    
    # Can't sell more than what's available
    prob += s[m] <= prev_inv + x[m], f"sell_limit_{m}"
    
    # Fixed cost linkage (Big-M constraint where M = warehouse_capacity)
    prob += x[m] <= warehouse_capacity * y[m], f"purchase_fixed_cost_link_{m}"
    if m == 2:
        prob += x[m] <= month2_bulk_receiving_threshold + warehouse_capacity * month2_bulk, 'month2_bulk_receiving_trigger'

# Solve
prob.solve(GUROBI_CMD(msg=0))

# Print results
obj_val = value(prob.objective)
print(f"OBJECTIVE_VALUE: {obj_val}")