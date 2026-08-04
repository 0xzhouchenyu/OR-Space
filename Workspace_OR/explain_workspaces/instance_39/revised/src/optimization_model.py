import os
import sys
import gurobi_pulp_compat as pulp

# Add parent directory to path if needed
script_dir = os.path.dirname(os.path.abspath(__file__))
# In the evaluation environment, data/ is a sibling of src/, so we must add the parent directory
parent_dir = os.path.abspath(os.path.join(script_dir, os.pardir))
sys.path.insert(0, script_dir)
sys.path.insert(0, parent_dir)

from utils import load_general_parameters

# Load data
data_dir = os.path.join(parent_dir, 'data')
params = load_general_parameters(os.path.join(data_dir, 'general_parameters.csv'))

# Extract parameters for owned fleet
motorcycle_pollution = params['motorcycle_pollution']
small_truck_pollution = params['small_truck_pollution']
large_truck_pollution = params['large_truck_pollution']

motorcycle_capacity = params['motorcycle_capacity']
small_truck_capacity = params['small_truck_capacity']
large_truck_capacity = params['large_truck_capacity']

max_motorcycle_trips = int(params['max_motorcycle_trips'])
max_total_trips = int(params['max_total_trips'])

# Demand parameters
demand_peak = params['demand_peak_units']
demand_offpeak = params['demand_offpeak_units']

# Leasing parameters
leasing_capacity = params['leasing_capacity']
leasing_pollution_per_unit = params['leasing_pollution_per_unit']
leasing_fixed_pollution = params['leasing_fixed_pollution']
max_leasing_fraction_peak = params['max_leasing_fraction_peak']

bigM_leasing = params['bigM_leasing']
epsilon = params['epsilon']

# Sets
methods = ['motorcycle', 'small_truck', 'large_truck']
periods = ['peak', 'offpeak']

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

# Build MILP model
prob = pulp.LpProblem("Daily_Transport_With_Leasing", pulp.LpMinimize)

# Decision variables
trips = {}
method_active = {}
M_trips = max_total_trips  # big-M for activation

for m in methods:
    for p in periods:
        trips[(m, p)] = pulp.LpVariable(f"trips_{m}_{p}", lowBound=0, cat='Integer')
        method_active[(m, p)] = pulp.LpVariable(f"method_active_{m}_{p}", lowBound=0, upBound=1, cat='Binary')

leasing_units_peak = pulp.LpVariable("leasing_units_peak", lowBound=0, cat='Continuous')
leasing_units_offpeak = pulp.LpVariable("leasing_units_offpeak", lowBound=0, cat='Continuous')
leasing_used = pulp.LpVariable("leasing_used", lowBound=0, upBound=1, cat='Binary')

# Objective: minimize total pollution
prob += (
    pulp.lpSum(pollution[m] * trips[(m, p)] for m in methods for p in periods)
    + leasing_pollution_per_unit * (leasing_units_peak + leasing_units_offpeak)
    + leasing_fixed_pollution * leasing_used
)

# Demand satisfaction constraints
prob += (
    capacity['motorcycle'] * trips[('motorcycle', 'peak')]
    + capacity['small_truck'] * trips[('small_truck', 'peak')]
    + capacity['large_truck'] * trips[('large_truck', 'peak')]
    + leasing_units_peak
    >= demand_peak
), "Peak_Demand"

prob += (
    capacity['motorcycle'] * trips[('motorcycle', 'offpeak')]
    + capacity['small_truck'] * trips[('small_truck', 'offpeak')]
    + capacity['large_truck'] * trips[('large_truck', 'offpeak')]
    + leasing_units_offpeak
    >= demand_offpeak
), "Offpeak_Demand"

# Motorcycle daily trip limit
prob += (
    trips[('motorcycle', 'peak')] + trips[('motorcycle', 'offpeak')]
    <= max_motorcycle_trips
), "Motorcycle_Trip_Limit"

# Total daily trip limit across all methods and periods
prob += (
    pulp.lpSum(trips[(m, p)] for m in methods for p in periods)
    <= max_total_trips
), "Total_Trip_Limit"

# Method activation coupling: trips and method_active
for m in methods:
    for p in periods:
        # Upper bound coupling
        prob += trips[(m, p)] <= M_trips * method_active[(m, p)], f"Trip_UB_{m}_{p}"
        # Lower bound to enforce activation implies at least one trip
        prob += trips[(m, p)] >= method_active[(m, p)], f"Trip_LB_{m}_{p}"

# Method count limit per period: at most 2 active methods per period
for p in periods:
    prob += (
        pulp.lpSum(method_active[(m, p)] for m in methods) <= 2
    ), f"Active_Method_Limit_{p}"

# Leasing capacity and activation
total_leasing = leasing_units_peak + leasing_units_offpeak

prob += total_leasing <= leasing_capacity, "Leasing_Capacity"
prob += total_leasing <= bigM_leasing * leasing_used, "Leasing_UB_Activation"
prob += total_leasing >= epsilon * leasing_used, "Leasing_LB_Activation"

# Leasing share limit in peak period
prob += leasing_units_peak <= max_leasing_fraction_peak * demand_peak, "Leasing_Peak_Share_Limit"

# Solve model
prob.solve(pulp.GUROBI_CMD(msg=0))

obj_val = pulp.value(prob.objective)

print(f"OBJECTIVE_VALUE: {obj_val}")
