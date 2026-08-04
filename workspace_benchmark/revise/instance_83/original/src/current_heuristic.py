import os
import csv
from gurobi_pulp_compat import *

# Load data
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# Read time periods and minimum waiters needed
time_periods = []
min_waiters = []
with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        time_periods.append(row['Time'].strip())
        min_waiters.append(int(row['Minimum_Number_of_Waiters_Needed'].strip()))

# Read general parameters
with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['Parameter_Name'].strip() == 'waiter_work_hours':
            work_hours = int(row['Value'].strip())

# Number of periods
n = len(time_periods)  # 6 periods, each 4 hours

# Each waiter works 8 hours = 2 consecutive 4-hour periods
# Periods indexed 0..5:
# 0: 2-6
# 1: 6-10
# 2: 10-14
# 3: 14-18
# 4: 18-22
# 5: 22-2

# x_i = number of waiters starting work at the beginning of period i
# Each waiter starting at period i works during periods i and (i+1) mod 6

prob = LpProblem("Restaurant_Waiters", LpMinimize)

# Decision variables
x = [LpVariable(f"x_{i}", lowBound=0, cat='Integer') for i in range(n)]

# Objective: minimize total number of waiters
prob += lpSum(x), "Total_Waiters"

# Constraints: for each period j, the number of waiters working >= min_waiters[j]
# Waiters working in period j are those who started in period j or period (j-1) mod n
for j in range(n):
    prev = (j - 1) % n
    prob += x[prev] + x[j] >= min_waiters[j], f"Period_{j}_{time_periods[j]}"

# Solve
prob.solve(GUROBI_CMD(msg=0))

# Print results
total = value(prob.objective)
for i in range(n):
    print(f"Waiters starting at period {time_periods[i]}: {int(value(x[i]))}")

print(f"OBJECTIVE_VALUE: {total}")