import os
import csv
from gurobi_pulp_compat import *

data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

params = {}
with open(os.path.join(data_dir, 'general_parameters.csv')) as f:
    for row in csv.DictReader(f):
        params[row['Parameter_Name'].strip()] = float(row['Value'])

products = {}
with open(os.path.join(data_dir, 'table_1.csv')) as f:
    for row in csv.DictReader(f):
        products[row['Product'].strip()] = {
            'a_hrs': float(row['Workshop_A_Hours']),
            'b_hrs': float(row['Workshop_B_Hours']),
            'insp_cost': float(row['Inspection_Sales_Cost'])
        }

m = products['Microwave_Oven']
w = products['Water_Heater']

prob = LpProblem("production", LpMaximize)
x1 = LpVariable("microwave", lowBound=params['microwave_minimum_sales'])
x2 = LpVariable("water_heater", lowBound=params['water_heater_minimum_sales'])

rev_m = m['a_hrs']*params['workshop_a_hourly_cost'] + m['b_hrs']*params['workshop_b_hourly_cost'] + m['insp_cost']
rev_w = w['a_hrs']*params['workshop_a_hourly_cost'] + w['b_hrs']*params['workshop_b_hourly_cost'] + w['insp_cost']

prob += rev_m*x1 + rev_w*x2
prob += m['a_hrs']*x1 + w['a_hrs']*x2 <= params['workshop_a_available_hours'] + params['workshop_a_overtime_limit']
prob += m['b_hrs']*x1 + w['b_hrs']*x2 >= params['workshop_b_available_hours']
prob += m['insp_cost']*x1 + w['insp_cost']*x2 <= params['inspection_sales_cost_limit']

prob.solve(GUROBI_CMD(msg=0))
print(f"OBJECTIVE_VALUE: {value(prob.objective)}")