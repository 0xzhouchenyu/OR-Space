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

initial_fund = params['initial_fund']
annual_rate = params['annual_profit_rate'] / 100
inv_limit_y1 = params['investment_limit_year1']
return_rate_y1y2 = params['return_rate_year1_to_year2'] / 100
inv_limit_y2 = params['investment_limit_year2']
return_rate_y2y3 = params['return_rate_year2_to_year3'] / 100
inv_limit_y3 = params['investment_limit_year3']
profit_rate_y3 = params['profit_rate_year3'] / 100

fee_y1 = params['fee_year1']
fee_y2 = params['fee_year2']
fee_y3 = params['fee_year3']

# Decision variables
prob = LpProblem("Investment_Optimization_With_Fees", LpMaximize)

a1 = LpVariable("a1", lowBound=0)
a2 = LpVariable("a2", lowBound=0)
a3 = LpVariable("a3", lowBound=0)

b1 = LpVariable("b1", lowBound=0, upBound=inv_limit_y1)
c2 = LpVariable("c2", lowBound=0, upBound=inv_limit_y2)
d3 = LpVariable("d3", lowBound=0, upBound=inv_limit_y3)

y_b1 = LpVariable("y_b1", cat='Binary')
y_c2 = LpVariable("y_c2", cat='Binary')
y_d3 = LpVariable("y_d3", cat='Binary')

# Big-M constraints for fixed costs
prob += b1 <= inv_limit_y1 * y_b1
prob += c2 <= inv_limit_y2 * y_c2
prob += d3 <= inv_limit_y3 * y_d3

# Budget constraints
prob += a1 + b1 <= initial_fund, "Year1_budget"
prob += a2 + c2 <= (initial_fund - a1 - b1) + a1 * (1 + annual_rate), "Year2_budget"
prob += a3 + d3 <= (initial_fund - a1 - b1) + a1*(1+annual_rate) - a2 - c2 + a2*(1+annual_rate) + b1*return_rate_y1y2, "Year3_budget"

# Objective
cash_year3 = (initial_fund - a1 - b1) + a1*(1+annual_rate) - a2 - c2 + a2*(1+annual_rate) + b1*return_rate_y1y2 - a3 - d3
total_end = cash_year3 + a3*(1+annual_rate) + c2*return_rate_y2y3 + d3*(1+profit_rate_y3)
total_net = total_end - fee_y1 * y_b1 - fee_y2 * y_c2 - fee_y3 * y_d3

prob += total_net, "Maximize_total_net"

prob.solve(GUROBI_CMD(msg=0))

obj_val = value(prob.objective)
print(f"Status: {LpStatus[prob.status]}")
print(f"OBJECTIVE_VALUE: {obj_val}")