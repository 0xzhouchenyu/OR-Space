import os
import csv
from utils import load_general_parameters

# Load data
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
params = load_general_parameters(os.path.join(data_dir, 'general_parameters.csv'))

# Extract parameters
m1_liquid = params['machine_1_time_per_liquid_lot']  # 50 min per lot
m2_liquid = params['machine_2_time_per_liquid_lot']  # 30 min per lot
m1_solid = params['machine_1_time_per_solid_lot']    # 24 min per lot
m2_solid = params['machine_2_time_per_solid_lot']    # 33 min per lot

init_liquid = params['initial_liquid_inventory']  # 30 lots
init_solid = params['initial_solid_inventory']    # 90 lots

m1_avail = params['machine_1_available_time'] * 60  # 40 hours -> 2400 minutes
m2_avail = params['machine_2_available_time'] * 60  # 35 hours -> 2100 minutes

demand_liquid = params['forecast_liquid_demand']  # 75 lots
demand_solid = params['forecast_solid_demand']    # 95 lots

# Decision variables:
# x_l = lots of liquid fertilizer produced
# x_s = lots of solid fertilizer produced
#
# Ending inventory:
# end_liquid = init_liquid + x_l - demand_liquid
# end_solid = init_solid + x_s - demand_solid
#
# Objective: maximize (end_liquid + end_solid)
#   = maximize (init_liquid + x_l - demand_liquid + init_solid + x_s - demand_solid)
#   = maximize (x_l + x_s) + constant
#
# Constraints:
# Machine 1: 50*x_l + 24*x_s <= 2400
# Machine 2: 30*x_l + 33*x_s <= 2100
# Demand satisfaction: x_l >= demand_liquid - init_liquid = 75 - 30 = 45
#                      x_s >= demand_solid - init_solid = 95 - 90 = 5
# Non-negativity: x_l >= 0, x_s >= 0

import gurobi_pulp_compat as pulp

prob = pulp.LpProblem("Fertilizer_Production", pulp.LpMaximize)

x_l = pulp.LpVariable("x_liquid", lowBound=0)
x_s = pulp.LpVariable("x_solid", lowBound=0)

# Ending inventories
end_liquid = init_liquid + x_l - demand_liquid
end_solid = init_solid + x_s - demand_solid

# Objective: maximize total ending inventory
prob += end_liquid + end_solid, "Total_Ending_Inventory"

# Machine constraints
prob += m1_liquid * x_l + m1_solid * x_s <= m1_avail, "Machine_1_Capacity"
prob += m2_liquid * x_l + m2_solid * x_s <= m2_avail, "Machine_2_Capacity"

# Demand satisfaction: ending inventory >= 0
prob += end_liquid >= 0, "Liquid_Demand_Satisfaction"
prob += end_solid >= 0, "Solid_Demand_Satisfaction"

prob.solve(pulp.GUROBI_CMD(msg=0))

# Calculate objective value
obj_val = pulp.value(prob.objective)

print(f"Status: {pulp.LpStatus[prob.status]}")
print(f"Liquid produced: {pulp.value(x_l):.4f} lots")
print(f"Solid produced: {pulp.value(x_s):.4f} lots")
print(f"Ending liquid inventory: {pulp.value(x_l) + init_liquid - demand_liquid:.4f}")
print(f"Ending solid inventory: {pulp.value(x_s) + init_solid - demand_solid:.4f}")
print(f"OBJECTIVE_VALUE: {obj_val:.2f}")