import os
import csv
from gurobi_pulp_compat import *
from utils import load_demand, load_parameters

data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# Load data
demand = load_demand(os.path.join(data_dir, 'table_1.csv'))
params = load_parameters(os.path.join(data_dir, 'general_parameters.csv'))

shift_duration = int(params['shift_duration'])  # 8 hours
regular_pay = float(params['regular_nurse_pay'])  # 10 yuan/hour
contract_pay = float(params['contract_nurse_pay'])  # 15 yuan/hour

num_periods = len(demand)  # 6 periods, each 4 hours
periods_per_shift = shift_duration // 4  # 2 periods per shift

# Decision variables: regular and contract nurses starting at each shift
prob = LpProblem("NurseScheduling", LpMinimize)

# x[j] = number of regular nurses starting shift j
# y[j] = number of contract nurses starting shift j
x = [LpVariable(f"x_{j}", lowBound=0, cat='Integer') for j in range(num_periods)]
y = [LpVariable(f"y_{j}", lowBound=0, cat='Integer') for j in range(num_periods)]

# Objective: minimize total cost
# Each nurse works 8 hours
cost = lpSum([(regular_pay * shift_duration) * x[j] + (contract_pay * shift_duration) * y[j] for j in range(num_periods)])
prob += cost

# Coverage constraints: for each time period i, sum of nurses from shifts that cover period i >= demand[i]
# Shift j covers periods j and (j+1) % num_periods
for i in range(num_periods):
    covering_shifts = []
    for j in range(num_periods):
        # Shift j covers periods j and (j+1) % num_periods
        covered = [j, (j + 1) % num_periods]
        if i in covered:
            covering_shifts.append(j)
    prob += lpSum([x[j] + y[j] for j in covering_shifts]) >= demand[i], f"Demand_period_{i}"

prob.solve(GUROBI_CMD(msg=0))

total_cost = value(prob.objective)

# Print solution details
for j in range(num_periods):
    print(f"Shift {j}: Regular={int(value(x[j]))}, Contract={int(value(y[j]))}")

print(f"OBJECTIVE_VALUE: {total_cost}")