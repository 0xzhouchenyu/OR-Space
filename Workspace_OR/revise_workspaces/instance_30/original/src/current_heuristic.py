import os
import csv
from utils import load_feed_data, load_general_parameters
import gurobi_pulp_compat as pulp

# Construct paths
base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(base_dir, '..', 'data')

# Load data
feeds = load_feed_data(os.path.join(data_dir, 'table_1.csv'))
params = load_general_parameters(os.path.join(data_dir, 'general_parameters.csv'))

min_protein = params['min_protein_requirement']
min_minerals = params['min_minerals_requirement']
min_vitamins = params['min_vitamins_requirement']

# Create LP problem
prob = pulp.LpProblem("MinimizeFeedCost", pulp.LpMinimize)

# Decision variables: amount of each feed (kg), non-negative
x = {}
for f in feeds:
    x[f['Feed']] = pulp.LpVariable(f"x_{f['Feed']}", lowBound=0, cat='Continuous')

# Objective: minimize total cost
prob += pulp.lpSum([f['Price_Y_per_kg'] * x[f['Feed']] for f in feeds]), "TotalCost"

# Constraints
# Protein constraint
prob += pulp.lpSum([f['Protein_g'] * x[f['Feed']] for f in feeds]) >= min_protein, "ProteinRequirement"

# Minerals constraint
prob += pulp.lpSum([f['Minerals_g'] * x[f['Feed']] for f in feeds]) >= min_minerals, "MineralsRequirement"

# Vitamins constraint
prob += pulp.lpSum([f['Vitamins_mg'] * x[f['Feed']] for f in feeds]) >= min_vitamins, "VitaminsRequirement"

# Solve
prob.solve(pulp.GUROBI_CMD(msg=0))

# Print results
for f in feeds:
    val = pulp.value(x[f['Feed']])
    print(f"Feed {f['Feed']}: {val:.6f} kg")

obj_val = pulp.value(prob.objective)
print(f"OBJECTIVE_VALUE: {obj_val}")