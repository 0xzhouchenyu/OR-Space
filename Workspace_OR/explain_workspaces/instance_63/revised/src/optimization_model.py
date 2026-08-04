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

horse_cost = params['horse_cost_per_trip']
bike_cost = params['bicycle_cost_per_trip']
cart_cost = params['handcart_cost_per_trip']
horse_fixed = params['horse_fixed_cost']
bike_fixed = params['bicycle_fixed_cost']
cart_fixed = params['handcart_fixed_cost']
poll_penalty = params['pollution_penalty_per_unit']
permit_threshold = params['horse_pollution_permit_threshold']
permit_fee = params['horse_pollution_permit_fee']

# Model
prob = LpProblem("FarmTransport_Revised", LpMinimize)

# Decision variables
x_horse = LpVariable("horse_trips", lowBound=0, cat='Integer')
x_bike = LpVariable("bike_trips", lowBound=0, cat='Integer')
x_cart = LpVariable("cart_trips", lowBound=0, cat='Integer')

z_horse = LpVariable("use_horse", cat='Binary')
z_bike = LpVariable("use_bike", cat='Binary')
z_cart = LpVariable("use_cart", cat='Binary')
pollution_permit = LpVariable("pollution_permit", cat='Binary')

M = 10000  # Big-M

# Total pollution
total_pollution = horse_poll * x_horse + bike_poll * x_bike + cart_poll * x_cart

# Objective: minimize total cost (variable + fixed + pollution penalty)
prob += (horse_cost * x_horse + bike_cost * x_bike + cart_cost * x_cart +
         horse_fixed * z_horse + bike_fixed * z_bike + cart_fixed * z_cart +
         poll_penalty * total_pollution + permit_fee * pollution_permit)

# Must transport at least min_produce
prob += horse_cap * x_horse + bike_cap * x_bike + cart_cap * x_cart >= min_produce

# Pollution constraint
prob += total_pollution <= max_poll
prob += total_pollution <= permit_threshold + M * pollution_permit

# Minimum horse trips
prob += x_horse >= min_horse

# Linking constraints for fixed costs
prob += x_horse <= M * z_horse
prob += x_bike <= M * z_bike
prob += x_cart <= M * z_cart

# Either bicycle or handcart, not both
prob += z_bike + z_cart <= 1

# Solve
prob.solve(GUROBI_CMD(msg=0))

obj_val = value(prob.objective)

print(f"Horse trips: {value(x_horse)}")
print(f"Bicycle trips: {value(x_bike)}")
print(f"Handcart trips: {value(x_cart)}")
print(f"OBJECTIVE_VALUE: {obj_val}")
