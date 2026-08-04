import os
import pandas as pd
from gurobi_pulp_compat import *

data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

gp = pd.read_csv(os.path.join(data_dir, 'general_parameters.csv'))
params = {r['Parameter_Name'].strip(): float(r['Value']) for _, r in gp.iterrows()}

tbl = pd.read_csv(os.path.join(data_dir, 'table_1.csv'))
tbl['Product'] = tbl['Product'].str.strip()
m = tbl[tbl['Product'] == 'Microwave_Oven'].iloc[0]
w = tbl[tbl['Product'] == 'Water_Heater'].iloc[0]

rev_m = m['Workshop_A_Hours']*params['workshop_a_hourly_cost'] + m['Workshop_B_Hours']*params['workshop_b_hourly_cost'] + m['Inspection_Sales_Cost']
rev_w = w['Workshop_A_Hours']*params['workshop_a_hourly_cost'] + w['Workshop_B_Hours']*params['workshop_b_hourly_cost'] + w['Inspection_Sales_Cost']

prob = LpProblem("production_revised", LpMaximize)
x_m = LpVariable("x_m", lowBound=params['microwave_minimum_sales'])
x_w = LpVariable("x_w", lowBound=params['water_heater_minimum_sales'])
z_m = LpVariable("z_m", cat='Binary')
z_w = LpVariable("z_w", cat='Binary')

prob += (rev_m + params['green_bonus_m'])*x_m + (rev_w + params['green_bonus_w'])*x_w

prob += m['Workshop_A_Hours']*x_m + w['Workshop_A_Hours']*x_w + params['setup_hours_A']*(z_m + z_w) <= params['workshop_a_available_hours'] + params['workshop_a_overtime_limit']
prob += m['Workshop_B_Hours']*x_m + w['Workshop_B_Hours']*x_w >= params['workshop_b_available_hours']
prob += m['Inspection_Sales_Cost']*x_m + w['Inspection_Sales_Cost']*x_w <= params['inspection_sales_cost_limit']
prob += x_m <= params['bigM']*z_m
prob += x_w <= params['bigM']*z_w
prob += params['tech_rate_m']*x_m + params['tech_rate_w']*x_w <= params['tech_pool_hours']
prob += z_m + z_w >= 1

prob.solve(GUROBI_CMD(msg=0))
print(f"OBJECTIVE_VALUE: {value(prob.objective)}")