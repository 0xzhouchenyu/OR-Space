import os
import csv
from gurobi_pulp_compat import *

# Load data
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# Load general parameters
with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['Parameter_Name'].strip() == 'initial_capital':
            initial_capital = float(row['Value'].strip())

# Load project data
projects = []
with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        projects.append(row)

# Create LP problem
prob = LpProblem("Investment_Maximization", LpMaximize)

# Decision variables
# x1_1: amount invested in Project 1 at beginning of Year 1
# x1_2: amount invested in Project 1 at beginning of Year 2
# x1_3: amount invested in Project 1 at beginning of Year 3
# x2: amount invested in Project 2 at beginning of Year 1
# x3: amount invested in Project 3 at beginning of Year 2
# x4: amount invested in Project 4 at beginning of Year 3

x1_1 = LpVariable("x1_1", lowBound=0)
x1_2 = LpVariable("x1_2", lowBound=0)
x1_3 = LpVariable("x1_3", lowBound=0)
x2 = LpVariable("x2", lowBound=0, upBound=120000)
x3 = LpVariable("x3", lowBound=0, upBound=150000)
x4 = LpVariable("x4", lowBound=0, upBound=100000)

# Year 1 budget constraint: x1_1 + x2 <= initial_capital
prob += x1_1 + x2 <= initial_capital, "Year1_Budget"

# Year 2 budget constraint: available cash = proceeds from x1_1 (matured same year = end of year 1)
# x1_1 * 1.20 is available at beginning of Year 2
# x1_2 + x3 <= x1_1 * 1.20
prob += x1_2 + x3 <= x1_1 * 1.20, "Year2_Budget"

# Year 3 budget constraint: proceeds from x1_2 (matures same year = end of year 2) + x2 matures end of year 2
# Available at beginning of Year 3: x1_2 * 1.20 + x2 * 1.50
prob += x1_3 + x4 <= x1_2 * 1.20 + x2 * 1.50 + x3 * 1.60, "Year3_Budget"

# Objective: total money at end of Year 3
# x1_3 matures end of Year 3: x1_3 * 1.20
# x4 matures end of Year 3: x4 * 1.40
prob += x1_3 * 1.20 + x4 * 1.40, "Total_End_Year3"

prob.solve(GUROBI_CMD(msg=0))

obj_val = value(prob.objective)
print(f"Status: {LpStatus[prob.status]}")
for v in prob.variables():
    print(f"{v.name} = {v.varValue}")
print(f"OBJECTIVE_VALUE: {obj_val}")