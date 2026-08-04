import os
from utils import load_general_parameters
import gurobi_pulp_compat as pulp

# Load data
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
params = load_general_parameters(os.path.join(data_dir, 'general_parameters.csv'))

# Extract parameters
profit_A = params['profit_per_kg_product_A']
profit_B = params['profit_per_kg_product_B']
max_hours = params['max_production_hours_per_week']
hours_A = params['hours_per_kg_product_A']
hours_B = params['hours_per_kg_product_B']
min_ratio_B_to_A = params['min_output_ratio_product_B_to_A']
storage_ratio_A_to_B = params['storage_space_ratio_product_A_to_B']
max_storage_A = params['max_storage_product_A']

# Create the LP problem
prob = pulp.LpProblem("Maximize_Profit", pulp.LpMaximize)

# Decision variables
x_A = pulp.LpVariable("product_A", lowBound=0)
x_B = pulp.LpVariable("product_B", lowBound=0)

# Objective function: maximize profit
prob += profit_A * x_A + profit_B * x_B, "Total_Profit"

# Constraints
# 1. Production time constraint
prob += hours_A * x_A + hours_B * x_B <= max_hours, "Production_Hours"

# 2. Market demand: B >= 3 * A
prob += x_B >= min_ratio_B_to_A * x_A, "Market_Demand"

# 3. Storage capacity constraint
# Storage space for A is 4 times that of B (per kg).
# Max storage capacity expressed in terms of product A is 4 kg.
# So if product A takes 4 units of space per kg and product B takes 1 unit per kg,
# total storage capacity = max_storage_A * storage_ratio_A_to_B = 4 * 4 = 16 units of space
# Constraint: 4*x_A + 1*x_B <= 16
max_storage_units = max_storage_A * storage_ratio_A_to_B
prob += storage_ratio_A_to_B * x_A + x_B <= max_storage_units, "Storage_Capacity"

# Solve
prob.solve(pulp.GUROBI_CMD(msg=0))

# Print results
print(f"Status: {pulp.LpStatus[prob.status]}")
print(f"Product A: {pulp.value(x_A):.4f} kg")
print(f"Product B: {pulp.value(x_B):.4f} kg")

obj_val = pulp.value(prob.objective)
print(f"OBJECTIVE_VALUE: {obj_val:.3f}")