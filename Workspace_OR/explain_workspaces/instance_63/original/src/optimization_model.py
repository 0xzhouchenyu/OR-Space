import os
import csv
from gurobi_pulp_compat import *

# Load data
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

params = {}
with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        params[row['Parameter_Name'].strip()] = float(row['Value'].strip())

produce = params['produce_to_transport']
horse_poll = params['horse_pollution_per_trip']
bike_poll = params['bicycle_pollution_per_trip']
cart_poll = params['handcart_pollution_per_trip']
max_poll = params['max_total_pollution']
min_horse = params['min_horse_trips']
horse_cap = params['horse_capacity_per_trip']
bike_cap = params['bicycle_capacity_per_trip']
cart_cap = params['handcart_capacity_per_trip']
min_produce = params['min_total_produce']

# Model
prob = LpProblem("FarmTransport", LpMinimize)

# Decision variables
x_horse = LpVariable("horse_trips", lowBound=0, cat='Integer')
x_bike = LpVariable("bike_trips", lowBound=0, cat='Integer')
x_cart = LpVariable("cart_trips", lowBound=0, cat='Integer')

# Binary variable: y=1 means bicycle chosen, y=0 means handcart chosen
y = LpVariable("choose_bike", cat='Binary')

M = 10000  # Big-M

# Objective: minimize total pollution
prob += horse_poll * x_horse + bike_poll * x_bike + cart_poll * x_cart

# Must transport at least min_produce
prob += horse_cap * x_horse + bike_cap * x_bike + cart_cap * x_cart >= min_produce

# Pollution constraint
prob += horse_poll * x_horse + bike_poll * x_bike + cart_poll * x_cart <= max_poll

# Minimum horse trips
prob += x_horse >= min_horse

# Either bicycle or handcart, not both
# If y=1, bicycle is allowed, handcart must be 0
# If y=0, handcart is allowed, bicycle must be 0
prob += x_bike <= M * y
prob += x_cart <= M * (1 - y)

# Solve
prob.solve(GUROBI_CMD(msg=0))

obj_val = value(prob.objective)

print(f"Horse trips: {value(x_horse)}")
print(f"Bicycle trips: {value(x_bike)}")
print(f"Handcart trips: {value(x_cart)}")
print(f"Choose bicycle: {value(y)}")
print(f"Total produce: {horse_cap * value(x_horse) + bike_cap * value(x_bike) + cart_cap * value(x_cart)}")
print(f"Total pollution: {obj_val}")
print(f"OBJECTIVE_VALUE: {obj_val}")