import os
import csv
from gurobi_pulp_compat import *

# Load data directory
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

# Read general parameters into a dictionary
params = {}
with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        params[row['Parameter_Name']] = float(row['Value'])

budget = params['budget']
scen_1_prob = params['scen_1_prob']
scen_2_prob = params['scen_2_prob']
scen_1_risky_multiplier = params['scen_1_risky_multiplier']
scen_2_risky_multiplier = params['scen_2_risky_multiplier']

# Risk control parameters
total_risky_budget = params['total_risky_budget']
per_property_risky_cap = params['per_property_risky_cap']
max_risky_properties = int(params['max_risky_properties'])

# Create optimization model
prob = LpProblem("RealEstateInvestment_RiskyStable", LpMaximize)

# Decision variables
x = {}  # purchase decision
s = {}  # stable fraction
r = {}  # risky fraction
y = {}  # risky activation

for p in properties:
    name = p['name']
    x[name] = LpVariable(f"x_{name}", cat='Binary')
    s[name] = LpVariable(f"s_{name}", lowBound=0, upBound=1, cat='Continuous')
    r[name] = LpVariable(f"r_{name}", lowBound=0, upBound=1, cat='Continuous')
    y[name] = LpVariable(f"y_{name}", cat='Binary')

# Objective: maximize expected annual income
# Expected income coefficient for risky fraction: scen_1_prob*m1 + scen_2_prob*m2
risk_coeff = scen_1_prob * scen_1_risky_multiplier + scen_2_prob * scen_2_risky_multiplier

objective_terms = []
for p in properties:
    name = p['name']
    base_income = p['income']
    # Stable part: coefficient is (scen_1_prob + scen_2_prob) = 1
    objective_terms.append(base_income * s[name])
    # Risky part: coefficient uses risk_coeff
    objective_terms.append(base_income * risk_coeff * r[name])

prob += lpSum(objective_terms)

# Budget constraint on acquisition costs
prob += lpSum(p['cost'] * x[p['name']] for p in properties) <= budget, "Acquisition_Budget"

# Mutual exclusion: Property_4 and Property_3 cannot both be purchased
prob += x['Property_4'] + x['Property_3'] <= 1, "Mutual_Exclusion_P3_P4"

# Fraction feasibility and linkage constraints per property
for p in properties:
    name = p['name']

    # Total fraction cannot exceed purchased indicator
    prob += s[name] + r[name] <= x[name], f"Frac_leq_x_{name}"

    # Per-property risky cap: r[p] <= per_property_risky_cap * x[p]
    prob += r[name] <= per_property_risky_cap * x[name], f"Risky_cap_{name}"

    # Risky activation linkage: r[p] <= y[p]
    prob += r[name] <= y[name], f"Risky_link1_{name}"

    # Risky activation linkage: y[p] <= x[p]
    prob += y[name] <= x[name], f"Risky_link2_{name}"

# Total risky budget: sum of acquisition costs of properties with any risky exposure
prob += lpSum(p['cost'] * y[p['name']] for p in properties) <= total_risky_budget, "Total_Risky_Budget"

# Maximum number of risky properties
prob += lpSum(y[p['name']] for p in properties) <= max_risky_properties, "Max_Risky_Properties"

# Solve the problem using Gurobi
prob.solve(GUROBI_CMD(msg=0))

# Optional: print decision variables for inspection
for p in properties:
    name = p['name']
    x_val = value(x[name])
    s_val = value(s[name])
    r_val = value(r[name])
    y_val = value(y[name])
    if x_val is None:
        x_val = 0
    if s_val is None:
        s_val = 0.0
    if r_val is None:
        r_val = 0.0
    if y_val is None:
        y_val = 0
    print(f"{name}: x={int(round(x_val))}, s={s_val:.4f}, r={r_val:.4f}, y={int(round(y_val))}")

obj_val = value(prob.objective)
if obj_val is None:
    obj_val = 0.0
print(f"OBJECTIVE_VALUE: {obj_val}")
