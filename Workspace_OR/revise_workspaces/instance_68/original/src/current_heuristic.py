import os
import sys
from gurobi_pulp_compat import *

# Add parent directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from utils import load_distances, load_parameters

# Load data
data_dir = os.path.join(script_dir, '..', 'data')
distances = load_distances(data_dir)
params = load_parameters(data_dir)

# Extract parameters
min_supply = {
    'A': params['min_coal_yard_A'],
    'B': params['min_coal_yard_B']
}

demand = {
    1: params['residential_area_1_demand'],
    2: params['residential_area_2_demand'],
    3: params['residential_area_3_demand']
}

coal_yards = ['A', 'B']
areas = [1, 2, 3]

# Create the LP problem
prob = LpProblem("Coal_Distribution", LpMinimize)

# Decision variables: amount of coal shipped from yard i to area j
x = {}
for yard in coal_yards:
    for area in areas:
        x[(yard, area)] = LpVariable(f"x_{yard}_{area}", lowBound=0)

# Objective: minimize total transportation cost (distance * amount)
prob += lpSum(distances[(yard, area)] * x[(yard, area)] 
              for yard in coal_yards for area in areas), "Total_Transportation_Cost"

# Constraints:
# 1. Each coal yard must supply at least its minimum requirement
for yard in coal_yards:
    prob += lpSum(x[(yard, area)] for area in areas) >= min_supply[yard], f"Min_Supply_{yard}"

# 2. Each residential area must receive exactly its demand
for area in areas:
    prob += lpSum(x[(yard, area)] for yard in coal_yards) == demand[area], f"Demand_{area}"

# Solve
prob.solve(GUROBI_CMD(msg=0))

# Print solution details
print(f"Status: {LpStatus[prob.status]}")
print()
for yard in coal_yards:
    for area in areas:
        val = value(x[(yard, area)])
        if val and val > 0:
            print(f"Coal Yard {yard} -> Area {area}: {val} tons (distance: {distances[(yard, area)]} km)")

print()
total_supply = {yard: sum(value(x[(yard, area)]) for area in areas) for yard in coal_yards}
for yard in coal_yards:
    print(f"Coal Yard {yard} total supply: {total_supply[yard]} tons (min: {min_supply[yard]})")

obj_val = value(prob.objective)
print(f"\nOBJECTIVE_VALUE: {obj_val}")