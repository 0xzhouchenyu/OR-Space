import os
import sys
from utils import load_parameters
import gurobi_pulp_compat as pulp

# Load data
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
params = load_parameters(os.path.join(data_dir, 'general_parameters.csv'))

# Extract parameters
a_p1 = params['product_a_process_1_time']
a_p2 = params['product_a_process_2_time']
b_p1 = params['product_b_process_1_time']
b_p2 = params['product_b_process_2_time']
T1 = params['available_time_process_1']
T2 = params['available_time_process_2']
T1_high = params['available_time_process_1_high']
T2_high = params['available_time_process_2_high']

c_per_b = params['byproduct_c_per_unit_b']
max_c_sales = params['max_byproduct_c_sales']
threshold_c = params['threshold_c']
bigM_disposal = params['bigM_disposal']

base_disposal_cost = params['disposal_cost_per_unit_c']
high_disposal_cost = params['disposal_cost_per_unit_c_high']

profit_a = params['profit_per_unit_a']
profit_b = params['profit_per_unit_b']
profit_c = params['profit_per_unit_c']

# Create the MILP problem
prob = pulp.LpProblem("MaxProfitWithModesAndPiecewiseDisposal", pulp.LpMaximize)

# Decision variables
xA = pulp.LpVariable("xA", lowBound=0)  # units of product A
xB = pulp.LpVariable("xB", lowBound=0)  # units of product B
cSold = pulp.LpVariable("cSold", lowBound=0)  # units of by-product C sold
cDispLow = pulp.LpVariable("cDispLow", lowBound=0)  # units of C disposed at base cost
cDispHigh = pulp.LpVariable("cDispHigh", lowBound=0)  # units of C disposed at high cost

# Binary mode selection variables
z1_high = pulp.LpVariable("z1_high", lowBound=0, upBound=1, cat=pulp.LpBinary)
z2_high = pulp.LpVariable("z2_high", lowBound=0, upBound=1, cat=pulp.LpBinary)

# Objective: maximize total profit
prob += (
    profit_a * xA
    + profit_b * xB
    + profit_c * cSold
    - base_disposal_cost * cDispLow
    - high_disposal_cost * cDispHigh
), "TotalProfitWithModesAndPiecewiseDisposal"

# Process 1 capacity with mode selection
prob += (
    a_p1 * xA + b_p1 * xB
    <= T1 + (T1_high - T1) * z1_high
), "Process1TimeMode"

# Process 2 capacity with mode selection
prob += (
    a_p2 * xA + b_p2 * xB
    <= T2 + (T2_high - T2) * z2_high
), "Process2TimeMode"

# High-throughput mutual exclusion constraint
prob += z1_high + z2_high <= 1, "MutualExclusionHighMode"

# By-product C balance
prob += cSold + cDispLow + cDispHigh == c_per_b * xB, "ByproductBalance"

# Maximum C that can be sold
prob += cSold <= max_c_sales, "MaxCSales"

# Piecewise disposal constraints
prob += cDispLow <= threshold_c, "LowDisposalCap"
prob += cDispLow + cDispHigh <= bigM_disposal, "TotalDisposalCap"

# Solve
prob.solve(pulp.GUROBI_CMD(msg=0))

obj_val = pulp.value(prob.objective)
print(f"OBJECTIVE_VALUE: {obj_val}")
