import os
import csv
import gurobi_pulp_compat as pulp

# Construct paths
base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(base_dir, '..', 'data')

feeds = []
with open(os.path.join(data_dir, 'table_1.csv'), 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        feeds.append({
            'Feed': int(row['Feed']),
            'Protein_g': float(row['Protein_g']),
            'Minerals_g': float(row['Minerals_g']),
            'Vitamins_mg': float(row['Vitamins_mg']),
            'Price_Y_per_kg': float(row['Price_Y_per_kg'])
        })

params = {}
with open(os.path.join(data_dir, 'general_parameters.csv'), 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        params[row['Parameter_Name']] = float(row['Value'])

min_protein = params['min_protein_requirement']
min_minerals = params['min_minerals_requirement']
min_vitamins = params['min_vitamins_requirement']

# Create LP problem
prob = pulp.LpProblem("MinimizeFeedCost", pulp.LpMinimize)

# Decision variables
x = {}
for f in feeds:
    x[f['Feed']] = pulp.LpVariable(f"x_{f['Feed']}", lowBound=0, cat='Continuous')

# Binary variables for mutual exclusion
y4 = pulp.LpVariable("y_4", cat='Binary')
y5 = pulp.LpVariable("y_5", cat='Binary')

# Objective
prob += pulp.lpSum([f['Price_Y_per_kg'] * x[f['Feed']] for f in feeds])

# Constraints
prob += pulp.lpSum([f['Protein_g'] * x[f['Feed']] for f in feeds]) >= min_protein
prob += pulp.lpSum([f['Minerals_g'] * x[f['Feed']] for f in feeds]) >= min_minerals
prob += pulp.lpSum([f['Vitamins_mg'] * x[f['Feed']] for f in feeds]) >= min_vitamins

# Mutual exclusion constraints (Big-M method)
M = 100000
prob += x[4] <= M * y4
prob += x[5] <= M * y5
prob += y4 + y5 <= 1

# Solve
prob.solve(pulp.GUROBI_CMD(msg=0))

obj_val = pulp.value(prob.objective)
print(f"OBJECTIVE_VALUE: {obj_val}")