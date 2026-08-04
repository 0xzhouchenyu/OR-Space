import os
import csv
from gurobi_pulp_compat import LpProblem, LpMaximize, LpVariable, lpSum, GUROBI_CMD, value

# Load data directory
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# Read time periods and minimum waiters needed
time_periods = []
min_waiters = []
with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        time_periods.append(row['Time'].strip())
        min_waiters.append(int(row['Minimum_Number_of_Waiters_Needed'].strip()))

n_periods = len(time_periods)  # should be 6

# Initialize parameter containers
peak_indicator = [0] * n_periods
quality_weight = [0.0] * n_periods
waiter_cost_per_shift = None
waiter_budget = None

# Read general parameters
with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        name = row['Parameter_Name'].strip()
        value_str = row['Value'].strip()
        try:
            value_num = float(value_str)
        except ValueError:
            continue
        if name == 'waiter_cost_per_shift':
            waiter_cost_per_shift = value_num
        elif name == 'waiter_budget':
            waiter_budget = value_num
        elif name.startswith('peak_'):
            idx = int(name.split('_')[1])
            peak_indicator[idx] = int(value_num)
        elif name.startswith('quality_'):
            idx = int(name.split('_')[1])
            quality_weight[idx] = float(value_num)

# Basic sanity checks
if waiter_cost_per_shift is None or waiter_budget is None:
    raise ValueError('waiter_cost_per_shift and waiter_budget must be defined in general_parameters.csv')

# Define allowed patterns based on peak/off-peak structure
pattern_indices = {}  # i -> list of pattern ids
coverage = {}         # (i,p,j) -> 0/1

for i in range(n_periods):
    pattern_indices[i] = []
    j1 = i
    j2 = (i + 1) % n_periods
    if peak_indicator[j1] != peak_indicator[j2]:
        p = 0
        pattern_indices[i].append(p)
        for j in range(n_periods):
            coverage[(i, p, j)] = 0
        coverage[(i, p, j1)] = 1
        coverage[(i, p, j2)] = 1

# Build optimization model
prob = LpProblem('Restaurant_Waiters_Service_Quality', LpMaximize)

# Decision variables: y[i,p] integer >= 0 specifying number of waiters on pattern (i,p)
y = {}
for i in range(n_periods):
    for p in pattern_indices[i]:
        y[(i, p)] = LpVariable(f'y_{i}_{p}', lowBound=0, cat='Integer')

# Compute waiters in each period as linear expressions
waiters_in_period = {}
for j in range(n_periods):
    expr_terms = []
    for i in range(n_periods):
        for p in pattern_indices[i]:
            if coverage.get((i, p, j), 0) == 1:
                expr_terms.append(y[(i, p)])
    if expr_terms:
        waiters_in_period[j] = lpSum(expr_terms)
    else:
        waiters_in_period[j] = lpSum([])

# Objective: maximize service quality score
prob += lpSum(quality_weight[j] * waiters_in_period[j] for j in range(n_periods)), 'Service_Quality_Score'

# Constraints: minimum coverage for each period
for j in range(n_periods):
    prob += waiters_in_period[j] >= min_waiters[j], f'MinCoverage_{j}_{time_periods[j]}'

# Budget constraint: total wage cost <= waiter_budget
total_shifts = lpSum(y[(i, p)] for i in range(n_periods) for p in pattern_indices[i])
prob += waiter_cost_per_shift * total_shifts <= waiter_budget, 'BudgetConstraint'

# Solve model
prob.solve(GUROBI_CMD(msg=0))

# Extract objective value
obj_value = value(prob.objective)

# Print schedule details
for i in range(n_periods):
    for p in pattern_indices[i]:
        v = y[(i, p)].varValue
        if v is None:
            v = 0
        print(f'Start period {time_periods[i]}, pattern {p}: {int(v)} waiters')

for j in range(n_periods):
    v = value(waiters_in_period[j])
    if v is None:
        v = 0
    print(f'Waiters in period {time_periods[j]}: {int(v)}')

print(f'OBJECTIVE_VALUE: {obj_value}')
