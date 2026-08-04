import os
import sys
from gurobi_pulp_compat import *

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import load_car_data, load_parameters

# Data directory
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# Load data
cars = load_car_data(data_dir)
params = load_parameters(data_dir)

num_cars = int(params['num_cars'])
max_length_one_side = params['max_length_one_side']

car_ids = list(cars.keys())
lengths = cars

# Model: minimize the maximum of the two sides
# x_i = 1 if car i is on side 1, 0 if on side 2
# side1 = sum(lambda_i * x_i), side2 = sum(lambda_i * (1 - x_i))
# minimize T where T >= side1 and T >= side2
# constraint: side1 <= max_length_one_side and side2 <= max_length_one_side

prob = LpProblem("ParkingMinStreetLength", LpMinimize)

# Decision variables
x = {i: LpVariable(f"x_{i}", cat='Binary') for i in car_ids}
T = LpVariable("T", lowBound=0)

# Objective: minimize T (the max side length)
prob += T

# Total length
total_length = sum(lengths[i] for i in car_ids)

# side1 = sum(lengths[i] * x[i])
side1 = lpSum(lengths[i] * x[i] for i in car_ids)
# side2 = total_length - side1

# T >= side1
prob += T >= side1, "T_geq_side1"
# T >= side2 = total_length - side1
prob += T >= total_length - side1, "T_geq_side2"

# Constraint: each side <= max_length_one_side
prob += side1 <= max_length_one_side, "max_side1"
prob += total_length - side1 <= max_length_one_side, "max_side2"

# Solve
prob.solve(GUROBI_CMD(msg=0))

# Extract solution
obj_val = value(T)

print(f"Status: {LpStatus[prob.status]}")
print(f"Total car length: {total_length}")
print(f"Side 1 length: {value(side1)}")
print(f"Side 2 length: {total_length - value(side1)}")
print(f"Cars on side 1: {[i for i in car_ids if value(x[i]) > 0.5]}")
print(f"Cars on side 2: {[i for i in car_ids if value(x[i]) < 0.5]}")
print(f"OBJECTIVE_VALUE: {obj_val}")