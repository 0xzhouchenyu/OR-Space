import os
import sys
from itertools import combinations
import gurobi_pulp_compat as pulp

# Add parent directory to path if needed
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from utils import load_general_parameters

# Load data
data_dir = os.path.join(script_dir, '..', 'data')
params = load_general_parameters(os.path.join(data_dir, 'general_parameters.csv'))

# Extract parameters
motorcycle_pollution = params['motorcycle_pollution']       # 40
small_truck_pollution = params['small_truck_pollution']     # 70
large_truck_pollution = params['large_truck_pollution']     # 100
max_motorcycle_trips = int(params['max_motorcycle_trips'])  # 8
motorcycle_capacity = params['motorcycle_capacity']         # 10
small_truck_capacity = params['small_truck_capacity']       # 20
large_truck_capacity = params['large_truck_capacity']       # 50
min_transport = params['min_transport_requirement']         # 300
max_total_trips = int(params['max_total_trips'])            # 20

# The company can only choose 2 out of 3 transportation methods.
# We enumerate all combinations of 2 methods and solve each, picking the best.

methods = ['motorcycle', 'small_truck', 'large_truck']

pollution = {
    'motorcycle': motorcycle_pollution,
    'small_truck': small_truck_pollution,
    'large_truck': large_truck_pollution
}

capacity = {
    'motorcycle': motorcycle_capacity,
    'small_truck': small_truck_capacity,
    'large_truck': large_truck_capacity
}

best_obj = float('inf')
best_solution = None
best_combo = None

for combo in combinations(methods, 2):
    prob = pulp.LpProblem(f"Transport_{'_'.join(combo)}", pulp.LpMinimize)
    
    # Decision variables: number of trips for each method (integer, non-negative)
    trips = {}
    for m in combo:
        trips[m] = pulp.LpVariable(f"trips_{m}", lowBound=0, cat='Integer')
    
    # Objective: minimize total pollution
    prob += pulp.lpSum([pollution[m] * trips[m] for m in combo])
    
    # Constraint: minimum transport requirement
    prob += pulp.lpSum([capacity[m] * trips[m] for m in combo]) >= min_transport
    
    # Constraint: maximum total trips
    prob += pulp.lpSum([trips[m] for m in combo]) <= max_total_trips
    
    # Constraint: motorcycle trips limit
    if 'motorcycle' in combo:
        prob += trips['motorcycle'] <= max_motorcycle_trips
    
    # Solve
    prob.solve(pulp.GUROBI_CMD(msg=0))
    
    if prob.status == pulp.constants.LpStatusOptimal:
        obj_val = pulp.value(prob.objective)
        if obj_val < best_obj:
            best_obj = obj_val
            best_solution = {m: pulp.value(trips[m]) for m in combo}
            best_combo = combo

# Print solution details
if best_solution is not None:
    print(f"Best combination: {best_combo}")
    for m in best_combo:
        print(f"  {m}: {best_solution[m]} trips")
    total_capacity = sum(capacity[m] * best_solution[m] for m in best_combo)
    print(f"Total transport capacity: {total_capacity}")
    print(f"Total pollution: {best_obj}")

print(f"OBJECTIVE_VALUE: {best_obj}")