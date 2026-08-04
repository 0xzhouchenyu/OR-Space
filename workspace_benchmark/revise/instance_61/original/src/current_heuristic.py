import os
import csv
from gurobi_pulp_compat import *

# Load data
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# Read device data
devices = []
with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        devices.append({
            'name': row['Device'].strip(),
            'prep_cost': float(row['Prep_Completion_Cost_Yuan'].strip()),
            'unit_cost': float(row['Unit_Production_Cost_Yuan_per_Unit'].strip()),
            'max_cap': float(row['Max_Processing_Capacity_Units'].strip())
        })

# Read general parameters
with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['Parameter_Name'].strip() == 'required_units':
            required_units = float(row['Value'].strip())

# Create the optimization model
prob = LpProblem("MinCostProduction", LpMinimize)

n = len(devices)

# Decision variables
# x_i: number of units produced on device i (continuous)
# y_i: binary variable indicating whether device i is used
x = [LpVariable(f"x_{devices[i]['name']}", lowBound=0, upBound=devices[i]['max_cap'], cat='Continuous') for i in range(n)]
y = [LpVariable(f"y_{devices[i]['name']}", cat='Binary') for i in range(n)]

# Objective: minimize total cost = sum of (prep_cost * y_i + unit_cost * x_i)
prob += lpSum([devices[i]['prep_cost'] * y[i] + devices[i]['unit_cost'] * x[i] for i in range(n)])

# Constraint: total production must equal required units
prob += lpSum(x) == required_units, "TotalProduction"

# Linking constraints: x_i <= max_cap * y_i (if device not used, no production)
for i in range(n):
    prob += x[i] <= devices[i]['max_cap'] * y[i], f"Link_{devices[i]['name']}"

# Solve
prob.solve(GUROBI_CMD(msg=0))

# Print results
for i in range(n):
    print(f"Device {devices[i]['name']}: used={int(value(y[i]))}, units={value(x[i]):.1f}")

obj_val = value(prob.objective)
print(f"OBJECTIVE_VALUE: {obj_val}")