import os
import sys
from utils import load_parameters
from gurobi_pulp_compat import *

# Load data
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
params = load_parameters(os.path.join(data_dir, 'general_parameters.csv'))

# Extract parameters
min_A = params['min_raw_material_A']
min_B = params['min_raw_material_B']
min_C = params['min_raw_material_C']

cap_A_a = params['warehouse_A_truck_capacity_A']
cap_A_b = params['warehouse_A_truck_capacity_B']
cap_A_c = params['warehouse_A_truck_capacity_C']
cost_A = params['warehouse_A_truck_cost']

cap_B_a = params['warehouse_B_truck_capacity_A']
cap_B_b = params['warehouse_B_truck_capacity_B']
cap_B_c = params['warehouse_B_truck_capacity_C']
cost_B = params['warehouse_B_truck_cost']

# Create the LP problem
prob = LpProblem("MinFreightCost", LpMinimize)

# Decision variables: number of trucks from warehouse A and B (integers, non-negative)
x = LpVariable("trucks_from_A", lowBound=0, cat='Integer')
y = LpVariable("trucks_from_B", lowBound=0, cat='Integer')

# Objective: minimize total freight cost
prob += cost_A * x + cost_B * y, "TotalFreightCost"

# Constraints: meet minimum raw material requirements
prob += cap_A_a * x + cap_B_a * y >= min_A, "RawMaterialA"
prob += cap_A_b * x + cap_B_b * y >= min_B, "RawMaterialB"
prob += cap_A_c * x + cap_B_c * y >= min_C, "RawMaterialC"

# Solve
prob.solve(GUROBI_CMD(msg=0))

# Output results
print(f"Status: {LpStatus[prob.status]}")
print(f"Trucks from Warehouse A: {int(value(x))}")
print(f"Trucks from Warehouse B: {int(value(y))}")
print(f"OBJECTIVE_VALUE: {value(prob.objective)}")