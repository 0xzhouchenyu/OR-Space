import os
import csv
from gurobi_pulp_compat import *

# Load data directory
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# Read device data
devices = []
with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        devices.append({
            'name': row['Device'].strip(),
            'prep_cost': float(row['Prep_Completion_Cost_Yuan'].strip()),
            'unit_cost': float(row['Unit_Production_Cost_Yuan_per_Unit'].strip()),
            'max_cap': float(row['Max_Processing_Capacity_Units'].strip())
        })

# Default containers for general parameters
required_units = None
params = {}

with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        name = row['Parameter_Name'].strip()
        val = float(row['Value'].strip())
        params[name] = val

# Extract required parameters
required_units = params['required_units']
energy_budget_peak = params['energy_budget_peak']
energy_budget_offpeak = params['energy_budget_offpeak']
energy_per_unit = {
    'A': params['energy_per_unit_A'],
    'B': params['energy_per_unit_B'],
    'C': params['energy_per_unit_C'],
    'D': params['energy_per_unit_D']
}
startup_energy = {
    'A': params['startup_energy_A'],
    'B': params['startup_energy_B'],
    'C': params['startup_energy_C'],
    'D': params['startup_energy_D']
}
startup_cost = params['startup_cost']
startup_budget = params['startup_budget']
energy_price_peak = params['energy_price_peak']
energy_price_offpeak = params['energy_price_offpeak']

# Periods
periods = ['peak', 'offpeak']
energy_budget = {
    'peak': energy_budget_peak,
    'offpeak': energy_budget_offpeak
}
energy_price = {
    'peak': energy_price_peak,
    'offpeak': energy_price_offpeak
}

# Create optimization model
prob = LpProblem("MinCostProduction_EnergyPeriods", LpMinimize)

n = len(devices)

device_names = [d['name'] for d in devices]
max_cap = {d['name']: d['max_cap'] for d in devices}
prep_cost = {d['name']: d['prep_cost'] for d in devices}
unit_cost = {d['name']: d['unit_cost'] for d in devices}

# Decision variables
# x[(i,p)]: units produced on device i in period p
x = LpVariable.dicts("x", ((i, p) for i in device_names for p in periods), lowBound=0, cat='Continuous')
# z[(i,p)]: 1 if device i is started / active in period p
z = LpVariable.dicts("z", ((i, p) for i in device_names for p in periods), lowBound=0, upBound=1, cat='Binary')
# y[i]: 1 if device i is used at all during the day
y = LpVariable.dicts("y", (i for i in device_names), lowBound=0, upBound=1, cat='Binary')

# Small epsilon for linking constraints
epsilon = 1e-3

# Objective function components
fixed_prep_cost = lpSum(prep_cost[i] * y[i] for i in device_names)
prod_cost = lpSum(unit_cost[i] * x[(i, p)] for i in device_names for p in periods)
startup_cost_term = lpSum(startup_cost * z[(i, p)] for i in device_names for p in periods)

# Electricity cost per period
energy_cost_term = lpSum(
    energy_price[p] * (
        lpSum(energy_per_unit[i] * x[(i, p)] + startup_energy[i] * z[(i, p)] for i in device_names)
    )
    for p in periods
)

prob += fixed_prep_cost + prod_cost + startup_cost_term + energy_cost_term

# 1. Demand satisfaction
prob += lpSum(x[(i, p)] for i in device_names for p in periods) == required_units, "TotalDemand"

# 2. Device daily capacity
for i in device_names:
    prob += lpSum(x[(i, p)] for p in periods) <= max_cap[i], f"DailyCap_{i}"

# 3. Link y[i] with x[i,p]
for i in device_names:
    # Upper bound: production only if y[i] = 1
    for p in periods:
        prob += x[(i, p)] <= max_cap[i] * y[i], f"YLinkUB_{i}_{p}"
    # Lower bound to force y[i] = 0 when no production
    prob += lpSum(x[(i, p)] for p in periods) >= epsilon * y[i], f"YLinkLB_{i}"

# 4. Link z[i,p] with x[i,p]
for i in device_names:
    for p in periods:
        # If not started in period p, no production
        prob += x[(i, p)] <= max_cap[i] * z[(i, p)], f"ZLinkUB_{i}_{p}"
        # If any production, must start in that period
        prob += x[(i, p)] >= epsilon * z[(i, p)], f"ZLinkLB_{i}_{p}"

# 5. Consistency between y[i] and z[i,p]
for i in device_names:
    for p in periods:
        prob += z[(i, p)] <= y[i], f"YZConsist_{i}_{p}"

# 6. Period energy budget constraints
for p in periods:
    prob += lpSum(energy_per_unit[i] * x[(i, p)] + startup_energy[i] * z[(i, p)] for i in device_names) <= energy_budget[p], f"EnergyBudget_{p}"

# 7. Daily startup budget constraint
prob += lpSum(startup_cost * z[(i, p)] for i in device_names for p in periods) <= startup_budget, "StartupBudget"

# Solve
prob.solve(GUROBI_CMD(msg=0))

obj_val = value(prob.objective)

# Optional: print solution details (not required for evaluation but helpful)
for i in device_names:
    for p in periods:
        xi = value(x[(i, p)])
        zi = value(z[(i, p)])
        if xi is None:
            xi = 0.0
        if zi is None:
            zi = 0.0
        print(f"Device {i}, period {p}: x={xi:.4f}, z={int(round(zi))}")
    yi = value(y[i])
    if yi is None:
        yi = 0.0
    print(f"Device {i}: y={int(round(yi))}")

print(f"OBJECTIVE_VALUE: {obj_val}")
