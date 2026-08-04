import os
import csv
from gurobi_pulp_compat import *

# Load data
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# Read property data
properties = []
with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        properties.append({
            'name': row['Property'],
            'income': float(row['Annual_Income']),
            'cost': float(row['Cost'])
        })

# Read general parameters
params = {}
with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        params[row['Parameter_Name']] = float(row['Value'])

budget = params['budget']

# Create optimization model
prob = LpProblem("RealEstateInvestment", LpMaximize)

# Decision variables: binary (buy or not)
x = {}
for p in properties:
    x[p['name']] = LpVariable(p['name'], cat='Binary')

# Objective: maximize annual income
prob += lpSum([p['income'] * x[p['name']] for p in properties])

# Budget constraint
prob += lpSum([p['cost'] * x[p['name']] for p in properties]) <= budget

# If Property 4 is purchased, Property 3 cannot be purchased
# x[Property_4] + x[Property_3] <= 1
prob += x['Property_4'] + x['Property_3'] <= 1

# Solve
prob.solve(GUROBI_CMD(msg=0))

# Print results
for p in properties:
    print(f"{p['name']}: {int(value(x[p['name']]))}")

obj_val = value(prob.objective)
print(f"OBJECTIVE_VALUE: {obj_val}")