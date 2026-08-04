import os
import csv
from gurobi_pulp_compat import *

# Load data
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# Read general parameters
params = {}
with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        params[row['Parameter_Name'].strip()] = float(row['Value'].strip())

weekly_production_time = params['weekly_production_time']       # 110 hours
fabric_production_rate = params['fabric_production_rate']       # 1000 meters/hour
min_curtain_fabric_sales = params['min_curtain_fabric_sales']   # 70000 meters
curtain_fabric_profit = params['curtain_fabric_profit']         # 2.5 yuan/meter
min_clothing_fabric_sales = params['min_clothing_fabric_sales'] # 45000 meters
clothing_fabric_profit = params['clothing_fabric_profit']       # 1.5 yuan/meter
max_overtime = params['max_overtime']                           # 10 hours

# Convert sales requirements to hours
min_curtain_hours = min_curtain_fabric_sales / fabric_production_rate  # 70 hours
min_clothing_hours = min_clothing_fabric_sales / fabric_production_rate  # 45 hours

# Decision variables
prob = LpProblem("Textile_Factory_Overtime_Minimization", LpMinimize)

x_clothing = LpVariable("clothing_hours", lowBound=min_clothing_hours)
x_curtain = LpVariable("curtain_hours", lowBound=min_curtain_hours)
overtime = LpVariable("overtime", lowBound=0, upBound=max_overtime)

# Objective: minimize overtime
prob += overtime, "Minimize_Overtime"

# Constraint: total production time = regular time + overtime
prob += x_clothing + x_curtain == weekly_production_time + overtime, "Production_Time_Balance"

# Solve
prob.solve(GUROBI_CMD(msg=0))

# Print results
print(f"Status: {LpStatus[prob.status]}")
print(f"Clothing fabric hours: {value(x_clothing)}")
print(f"Curtain fabric hours: {value(x_curtain)}")
print(f"Overtime hours: {value(overtime)}")
print(f"Clothing fabric produced: {value(x_clothing) * fabric_production_rate} meters")
print(f"Curtain fabric produced: {value(x_curtain) * fabric_production_rate} meters")

obj_val = value(prob.objective)
print(f"OBJECTIVE_VALUE: {obj_val}")