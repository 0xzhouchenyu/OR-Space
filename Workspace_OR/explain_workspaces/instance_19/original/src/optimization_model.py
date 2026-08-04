import os
import csv
from utils import load_general_parameters

# Load data
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
params = load_general_parameters(os.path.join(data_dir, 'general_parameters.csv'))

# Extract parameters
cost_A = params['cost_per_chair_A']       # 50 USD per chair
cost_B = params['cost_per_chair_B']       # 45 USD per chair
cost_C = params['cost_per_chair_C']       # 40 USD per chair
chairs_per_order_A = params['chairs_per_order_A']  # 15 chairs per order
chairs_per_order_B = params['chairs_per_order_B']  # 10 chairs per order
chairs_per_order_C = params['chairs_per_order_C']  # 10 chairs per order
min_total = params['min_total_chairs']    # 100
max_total = params['max_total_chairs']    # 500
min_chairs_B_if_A = params['min_chairs_B_if_A']  # 10 chairs from B if ordering from A
dependency_B_C = params['dependency_B_C']  # if B ordered, must also order C

import gurobi_pulp_compat as pulp

# Create the problem
prob = pulp.LpProblem("FurnitureOrder", pulp.LpMinimize)

# Decision variables: number of orders from each manufacturer (integer, >= 0)
# We need upper bounds. Max total chairs is 500.
max_orders_A = max_total // int(chairs_per_order_A) + 1
max_orders_B = max_total // int(chairs_per_order_B) + 1
max_orders_C = max_total // int(chairs_per_order_C) + 1

x_A = pulp.LpVariable("orders_A", lowBound=0, upBound=max_orders_A, cat='Integer')
x_B = pulp.LpVariable("orders_B", lowBound=0, upBound=max_orders_B, cat='Integer')
x_C = pulp.LpVariable("orders_C", lowBound=0, upBound=max_orders_C, cat='Integer')

# Binary variables to indicate if we order from each manufacturer
y_A = pulp.LpVariable("y_A", cat='Binary')
y_B = pulp.LpVariable("y_B", cat='Binary')
y_C = pulp.LpVariable("y_C", cat='Binary')

# Total chairs from each manufacturer
chairs_A = chairs_per_order_A * x_A
chairs_B = chairs_per_order_B * x_B
chairs_C = chairs_per_order_C * x_C

# Objective: minimize total cost
# Cost is per chair, so total cost = cost_per_chair * number_of_chairs
prob += cost_A * chairs_A + cost_B * chairs_B + cost_C * chairs_C, "TotalCost"

# Constraint: total chairs between min and max
prob += chairs_A + chairs_B + chairs_C >= min_total, "MinChairs"
prob += chairs_A + chairs_B + chairs_C <= max_total, "MaxChairs"

# Big M for linking
M = max_total + 1

# Link y variables to x variables
# If x_A > 0 then y_A = 1
prob += x_A <= M * y_A, "LinkA1"
prob += x_A >= y_A, "LinkA2"  # if y_A=1 then at least 1 order

prob += x_B <= M * y_B, "LinkB1"
prob += x_B >= y_B, "LinkB2"

prob += x_C <= M * y_C, "LinkC1"
prob += x_C >= y_C, "LinkC2"

# Dependency: if ordering from A, must order at least min_chairs_B_if_A chairs from B
# chairs_B >= min_chairs_B_if_A * y_A
prob += chairs_B >= min_chairs_B_if_A * y_A, "DepAB"

# Dependency: if ordering from B, must also order from C
# y_B <= y_C (if B is used, C must be used)
prob += y_B <= y_C, "DepBC"

# Solve
prob.solve(pulp.GUROBI_CMD(msg=0))

# Extract results
obj_val = pulp.value(prob.objective)

print(f"Status: {pulp.LpStatus[prob.status]}")
print(f"Orders from A: {pulp.value(x_A)}, Chairs: {pulp.value(x_A) * chairs_per_order_A}")
print(f"Orders from B: {pulp.value(x_B)}, Chairs: {pulp.value(x_B) * chairs_per_order_B}")
print(f"Orders from C: {pulp.value(x_C)}, Chairs: {pulp.value(x_C) * chairs_per_order_C}")
total_chairs = (pulp.value(x_A) * chairs_per_order_A + 
                pulp.value(x_B) * chairs_per_order_B + 
                pulp.value(x_C) * chairs_per_order_C)
print(f"Total chairs: {total_chairs}")
print(f"OBJECTIVE_VALUE: {obj_val}")