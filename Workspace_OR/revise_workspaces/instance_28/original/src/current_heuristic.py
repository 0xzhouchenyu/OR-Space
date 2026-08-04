import os
import csv
from gurobi_pulp_compat import *

# Load data
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

params = {}
with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        params[row['Parameter_Name'].strip()] = float(row['Value'].strip())

initial_fund = params['initial_fund']  # 300000
annual_rate = params['annual_profit_rate'] / 100  # 0.20
inv_limit_y1 = params['investment_limit_year1']  # 150000
return_rate_y1y2 = params['return_rate_year1_to_year2'] / 100  # 1.50
inv_limit_y2 = params['investment_limit_year2']  # 200000
return_rate_y2y3 = params['return_rate_year2_to_year3'] / 100  # 1.60
inv_limit_y3 = params['investment_limit_year3']  # 100000
profit_rate_y3 = params['profit_rate_year3'] / 100  # 0.40

# Decision variables
prob = LpProblem("Investment_Optimization", LpMaximize)

# a1, a2, a3: amount invested in annual 20% investment at beginning of year 1, 2, 3
a1 = LpVariable("a1", lowBound=0)
a2 = LpVariable("a2", lowBound=0)
a3 = LpVariable("a3", lowBound=0)

# b1: 2-year investment at beginning of year 1 (returns end of year 2), max 150000
b1 = LpVariable("b1", lowBound=0, upBound=inv_limit_y1)

# c2: 2-year investment at beginning of year 2 (returns end of year 3), max 200000
c2 = LpVariable("c2", lowBound=0, upBound=inv_limit_y2)

# d3: special 1-year investment at beginning of year 3, max 100000
d3 = LpVariable("d3", lowBound=0, upBound=inv_limit_y3)

# Budget constraint at beginning of Year 1:
# a1 + b1 <= initial_fund
prob += a1 + b1 <= initial_fund, "Year1_budget"

# Budget constraint at beginning of Year 2:
# Available: a1*(1+0.20) (return from annual investment year 1) + leftover from year 1
# Leftover from year 1 = initial_fund - a1 - b1 (but this is cash, no interest on idle cash)
# Actually idle cash just stays as cash.
# a2 + c2 <= (initial_fund - a1 - b1) + a1*(1 + annual_rate)
prob += a2 + c2 <= (initial_fund - a1 - b1) + a1 * (1 + annual_rate), "Year2_budget"

# Budget constraint at beginning of Year 3:
# Available: cash from year 2 + a2*(1+0.20) + b1*1.50
# Cash from year 2 = (funds available at year 2) - a2 - c2
# funds_year2 = (initial_fund - a1 - b1) + a1*(1+annual_rate)
prob += a3 + d3 <= (initial_fund - a1 - b1) + a1*(1+annual_rate) - a2 - c2 + a2*(1+annual_rate) + b1*return_rate_y1y2, "Year3_budget"

# Objective: total funds at end of year 3
# End of year 3: cash leftover from year 3 + a3*(1+0.20) + c2*1.60 + d3*(1+0.40)
cash_year3 = (initial_fund - a1 - b1) + a1*(1+annual_rate) - a2 - c2 + a2*(1+annual_rate) + b1*return_rate_y1y2 - a3 - d3
total_end = cash_year3 + a3*(1+annual_rate) + c2*return_rate_y2y3 + d3*(1+profit_rate_y3)

prob += total_end, "Maximize_total"

prob.solve(GUROBI_CMD(msg=0))

obj_val = value(prob.objective)
print(f"Status: {LpStatus[prob.status]}")
print(f"a1={value(a1)}, b1={value(b1)}, a2={value(a2)}, c2={value(c2)}, a3={value(a3)}, d3={value(d3)}")
print(f"OBJECTIVE_VALUE: {obj_val}")