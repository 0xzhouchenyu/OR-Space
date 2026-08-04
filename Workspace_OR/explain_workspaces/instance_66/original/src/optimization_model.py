import os
import csv
from gurobi_pulp_compat import *

# Load data
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# Read table_1.csv
toys = []
with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        toys.append({
            'type': row['Toy_Type'],
            'labor': float(row['Manufacturing_Labor_Hours']),
            'inspection': float(row['Inspection_Hours']),
            'profit': float(row['Profit_Per_Unit'])
        })

# Read general_parameters.csv
params = {}
with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        params[row['Parameter_Name']] = float(row['Value'])

available_labor = params['available_labor_hours']
available_inspection = params['available_inspection_hours']
max_demand = {
    'High-End': params['max_demand_high_end'],
    'Mid-Range': params['max_demand_mid_range'],
    'Low-End': params['max_demand_low_end']
}

# Build optimization model
prob = LpProblem("ToyProduction", LpMaximize)

# Decision variables
x = {}
for toy in toys:
    x[toy['type']] = LpVariable(f"x_{toy['type']}", lowBound=0, cat='Continuous')

# Objective: maximize profit
prob += lpSum(toy['profit'] * x[toy['type']] for toy in toys), "Total_Profit"

# Constraints
# Labor hours
prob += lpSum(toy['labor'] * x[toy['type']] for toy in toys) <= available_labor, "Labor_Hours"

# Inspection hours
prob += lpSum(toy['inspection'] * x[toy['type']] for toy in toys) <= available_inspection, "Inspection_Hours"

# Demand constraints
for toy in toys:
    prob += x[toy['type']] <= max_demand[toy['type']], f"Demand_{toy['type']}"

# Solve
prob.solve(GUROBI_CMD(msg=0))

# Print results
for toy in toys:
    print(f"{toy['type']}: {value(x[toy['type']])}")

obj_val = value(prob.objective)
print(f"OBJECTIVE_VALUE: {obj_val}")