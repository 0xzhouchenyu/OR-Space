import os
import sys
from gurobi_pulp_compat import *

# Add parent directory to path if needed
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from utils import load_table_1, load_general_parameters

# Load data
data_dir = os.path.join(script_dir, '..', 'data')
weeks_data = load_table_1(data_dir)
params = load_general_parameters(data_dir)

storage_cost = params['storage_cost_per_thousand_boxes']
n_weeks = len(weeks_data)

# Create the LP problem
prob = LpProblem("Beverage_Production_Planning", LpMinimize)

# Decision variables
# x[t] = production in week t (in thousand boxes)
# s[t] = inventory at end of week t (in thousand boxes)
x = [LpVariable(f"x_{t+1}", lowBound=0, upBound=weeks_data[t]['capacity']) for t in range(n_weeks)]
s = [LpVariable(f"s_{t+1}", lowBound=0) for t in range(n_weeks)]

# Objective: minimize total production cost + storage cost
prob += lpSum(weeks_data[t]['cost'] * x[t] for t in range(n_weeks)) + \
        lpSum(storage_cost * s[t] for t in range(n_weeks))

# Constraints: inventory balance
# Assume initial inventory is 0
# For week 1: x[0] - s[0] = demand[0]  (i.e., s[0] = x[0] - demand[0])
# For week t>1: s[t-1] + x[t] - s[t] = demand[t]

for t in range(n_weeks):
    if t == 0:
        prob += x[t] - s[t] == weeks_data[t]['demand'], f"balance_week_{t+1}"
    else:
        prob += s[t-1] + x[t] - s[t] == weeks_data[t]['demand'], f"balance_week_{t+1}"

# Solve
prob.solve(GUROBI_CMD(msg=0))

# Print results
print(f"Status: {LpStatus[prob.status]}")
for t in range(n_weeks):
    print(f"Week {t+1}: Produce {value(x[t]):.1f}, Inventory {value(s[t]):.1f}")

obj_val = value(prob.objective)
print(f"OBJECTIVE_VALUE: {obj_val}")