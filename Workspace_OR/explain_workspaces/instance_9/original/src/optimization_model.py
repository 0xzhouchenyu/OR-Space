import os
from utils import load_toy_data, load_general_parameters
from gurobi_pulp_compat import *

# Load data
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
toys = load_toy_data(os.path.join(data_dir, 'table_1.csv'))
params = load_general_parameters(os.path.join(data_dir, 'general_parameters.csv'))

available_wood = params['available_wood']
available_steel = params['available_steel']

# Big M (upper bound on production quantity)
M = 1000

# Create problem
prob = LpProblem("HausToys", LpMaximize)

# Decision variables - quantities
x = {}
for t in toys:
    x[t['type']] = LpVariable(f"x_{t['type']}", lowBound=0, cat='Continuous')

# Binary variables - whether to manufacture
y = {}
for t in toys:
    y[t['type']] = LpVariable(f"y_{t['type']}", cat='Binary')

# Objective: maximize profit
prob += lpSum([t['profit'] * x[t['type']] for t in toys]), "Total_Profit"

# Resource constraints
prob += lpSum([t['wood'] * x[t['type']] for t in toys]) <= available_wood, "Wood_Constraint"
prob += lpSum([t['steel'] * x[t['type']] for t in toys]) <= available_steel, "Steel_Constraint"

# Linking constraints: x_i <= M * y_i
for t in toys:
    prob += x[t['type']] <= M * y[t['type']], f"Link_{t['type']}"

# Truck-train exclusion: if trucks manufactured, no trains
prob += y['truck'] + y['train'] <= 1, "Truck_Train_Exclusion"

# Boat-airplane dependency: if boats manufactured, airplanes must be too
prob += y['boat'] <= y['airplane'], "Boat_Airplane_Dependency"

# Boat-train limit: number of boats <= number of trains
prob += x['boat'] <= x['train'], "Boat_Train_Limit"

# Solve
prob.solve(GUROBI_CMD(msg=0))

# Print results
print(f"Status: {LpStatus[prob.status]}")
for t in toys:
    print(f"{t['type']}: {value(x[t['type']]):.2f} (manufacture: {value(y[t['type']])})")

obj_val = value(prob.objective)
print(f"OBJECTIVE_VALUE: {obj_val}")