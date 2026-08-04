import os
import csv
from utils import load_parameters

# Load data
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
params = load_parameters(os.path.join(data_dir, 'general_parameters.csv'))

# Extract parameters
cow_price = params['cow_selling_price']
sheep_price = params['sheep_selling_price']
chicken_price = params['chicken_selling_price']
cow_feed = params['cow_feed_cost']
sheep_feed = params['sheep_feed_cost']
chicken_feed = params['chicken_feed_cost']
cow_manure = params['cow_manure_production']
sheep_manure = params['sheep_manure_production']
chicken_manure = params['chicken_manure_production']
max_manure = params['max_manure_capacity']
max_chickens = params['max_chickens']
min_cows = params['min_cows']
min_sheep = params['min_sheep']
max_total = params['max_total_animals']

# Profit per animal
# cow: 500 - 100 = 400
# sheep: 200 - 80 = 120
# chicken: 8 - 5 = 3

import gurobi_pulp_compat as pulp

prob = pulp.LpProblem("FarmProfit", pulp.LpMaximize)

cows = pulp.LpVariable("cows", lowBound=min_cows, cat='Integer')
sheep = pulp.LpVariable("sheep", lowBound=min_sheep, cat='Integer')
chickens = pulp.LpVariable("chickens", lowBound=0, upBound=max_chickens, cat='Integer')

# Objective: maximize profit
prob += (cow_price - cow_feed) * cows + (sheep_price - sheep_feed) * sheep + (chicken_price - chicken_feed) * chickens

# Constraints
# Manure capacity
prob += cow_manure * cows + sheep_manure * sheep + chicken_manure * chickens <= max_manure

# Total animals
prob += cows + sheep + chickens <= max_total

# Solve
prob.solve(pulp.GUROBI_CMD(msg=0))

obj_val = pulp.value(prob.objective)
print(f"Cows: {pulp.value(cows)}")
print(f"Sheep: {pulp.value(sheep)}")
print(f"Chickens: {pulp.value(chickens)}")
print(f"OBJECTIVE_VALUE: {obj_val}")