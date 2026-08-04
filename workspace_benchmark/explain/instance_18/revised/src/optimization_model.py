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

weekly_production_time = params['weekly_production_time']
fabric_production_rate = params['fabric_production_rate']
min_curtain_fabric_sales = params['min_curtain_fabric_sales']
min_clothing_fabric_sales = params['min_clothing_fabric_sales']

# New parameters for shift capacities and overtime
day_shift_regular_capacity = params['day_shift_regular_capacity']
night_shift_regular_capacity = params['night_shift_regular_capacity']

day_overtime_limit = params['day_overtime_limit']
night_overtime_limit = params['night_overtime_limit']

day_overtime_penalty = params['day_overtime_penalty']
night_overtime_penalty = params['night_overtime_penalty']

day_min_utilization_ratio = params['day_min_utilization_ratio']
night_min_utilization_ratio = params['night_min_utilization_ratio']

# Convert sales requirements to hours
min_curtain_hours = min_curtain_fabric_sales / fabric_production_rate
min_clothing_hours = min_clothing_fabric_sales / fabric_production_rate

# Problem definition
prob = LpProblem("Textile_Factory_Two_Shift_Overtime_Minimization", LpMinimize)

# Decision variables
# Regular hours per shift
day_regular_hours = LpVariable("day_regular_hours", lowBound=0)
night_regular_hours = LpVariable("night_regular_hours", lowBound=0)

# Overtime hours per shift
day_overtime_hours = LpVariable("day_overtime_hours", lowBound=0, upBound=day_overtime_limit)
night_overtime_hours = LpVariable("night_overtime_hours", lowBound=0, upBound=night_overtime_limit)

# Product-specific production hours per shift
day_clothing_hours = LpVariable("day_clothing_hours", lowBound=0)
night_clothing_hours = LpVariable("night_clothing_hours", lowBound=0)

day_curtain_hours = LpVariable("day_curtain_hours", lowBound=0)
night_curtain_hours = LpVariable("night_curtain_hours", lowBound=0)

# Objective: minimize total overtime penalty cost
prob += day_overtime_penalty * day_overtime_hours + night_overtime_penalty * night_overtime_hours, "Minimize_Overtime_Penalty"

# 1) Total regular hours equal weekly production time and respect per-shift capacities
prob += day_regular_hours + night_regular_hours == weekly_production_time, "Regular_Time_Balance"
prob += day_regular_hours <= day_shift_regular_capacity, "Day_Regular_Capacity"
prob += night_regular_hours <= night_shift_regular_capacity, "Night_Regular_Capacity"

# 2) Shift utilization ratios
prob += day_regular_hours >= day_min_utilization_ratio * (day_regular_hours + night_regular_hours), "Day_Min_Utilization"
prob += night_regular_hours >= night_min_utilization_ratio * (day_regular_hours + night_regular_hours), "Night_Min_Utilization"

# 3) Shift-wise production capacity using regular + overtime
prob += day_clothing_hours + day_curtain_hours <= day_regular_hours + day_overtime_hours, "Day_Production_Capacity"
prob += night_clothing_hours + night_curtain_hours <= night_regular_hours + night_overtime_hours, "Night_Production_Capacity"

# 4) Demand (minimum production) constraints in hours
prob += day_clothing_hours + night_clothing_hours >= min_clothing_hours, "Clothing_Demand"
prob += day_curtain_hours + night_curtain_hours >= min_curtain_hours, "Curtain_Demand"

# Solve
prob.solve(GUROBI_CMD(msg=0))

obj_val = value(prob.objective)
print(f"OBJECTIVE_VALUE: {obj_val}")
