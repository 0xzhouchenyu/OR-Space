import os
import csv
from gurobi_pulp_compat import *

base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# Load general parameters
initial_capital = None
with open(os.path.join(base_dir, 'general_parameters.csv'), 'r', newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['Parameter_Name'].strip() == 'initial_capital':
            initial_capital = float(row['Value'].strip())

# Load project data
projects = {}
with open(os.path.join(base_dir, 'table_1.csv'), 'r', newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        pid = int(row['Project_ID'])
        projects[pid] = row

# Load liquidity policy
min_year3_reserve = None
reserve_shortfall_penalty = None
with open(os.path.join(base_dir, 'liquidity_policy.csv'), 'r', newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        name = row['Parameter_Name'].strip()
        val = float(row['Value'].strip())
        if name == 'min_year3_reserve':
            min_year3_reserve = val
        elif name == 'reserve_shortfall_penalty':
            reserve_shortfall_penalty = val

# Parameters from project table
r1 = float(projects[1]['Interest_Rate'])
r2 = float(projects[2]['Interest_Rate'])
r3 = float(projects[3]['Interest_Rate'])
r4 = float(projects[4]['Interest_Rate'])
cap2 = float(projects[2]['Investment_Capacity'])
cap3 = float(projects[3]['Investment_Capacity'])
cap4 = float(projects[4]['Investment_Capacity'])

# Model
prob = LpProblem('Investment_With_Liquidity_Penalty', LpMaximize)

# Decision variables
x1_1 = LpVariable('x1_1', lowBound=0)
x1_2 = LpVariable('x1_2', lowBound=0)
x1_3 = LpVariable('x1_3', lowBound=0)
x2 = LpVariable('x2', lowBound=0, upBound=cap2)
x3 = LpVariable('x3', lowBound=0, upBound=cap3)
x4 = LpVariable('x4', lowBound=0, upBound=cap4)

# Reserve (uninvested cash carried from beginning of Year 3 to end of Year 3) and shortfall
reserve_y3 = LpVariable('reserve_y3', lowBound=0)
shortfall = LpVariable('shortfall', lowBound=0)

# Budgets
prob += x1_1 + x2 <= initial_capital, 'Year1_Budget'
prob += x1_2 + x3 <= x1_1 * r1, 'Year2_Budget'

available_y3 = x1_2 * r1 + x2 * r2 + x3 * r3
prob += x1_3 + x4 + reserve_y3 == available_y3, 'Year3_Cash_Balance'

# Shortfall definition (relative to required reserve threshold at beginning of Year 3)
prob += shortfall >= min_year3_reserve - reserve_y3, 'Shortfall_Definition'

# Objective: total cash realized at end of Year 3 (matured investments + uninvested reserve carried forward)
# minus penalty for reserve shortfall at beginning of Year 3.
prob += x1_3 * r1 + x4 * r4 + reserve_y3 - reserve_shortfall_penalty * shortfall, 'Net_Objective'

prob.solve(GUROBI_CMD(msg=0))

value = float(prob.objective.value())
print(f"OBJECTIVE_VALUE: {value}")
