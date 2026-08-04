import os
import sys
import csv
from gurobi_pulp_compat import *

# Add parent directory to path if needed
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from utils import load_table_1, load_general_parameters

# Load data
data_dir = os.path.join(script_dir, '..', 'data')
products, equipment_names, processing_times, effective_hours, base_profit = load_table_1(data_dir)
params = load_general_parameters(data_dir)

# Extract scalar parameters
try:
    overtime_hours_cap = float(params["overtime_hours_cap"])  # hours
    overtime_cost_multiplier = float(params["overtime_cost_multiplier"])  # dimensionless
    min_prod = {
        'I': float(params.get('min_prod_I', 0.0)),
        'II': float(params.get('min_prod_II', 0.0)),
        'III': float(params.get('min_prod_III', 0.0))
    }
except KeyError as e:
    raise KeyError(f"Missing required parameter in general_parameters.csv: {e}")

# Create the LP problem: we now minimize total cost
prob = LpProblem("Factory_Production_Optimization_With_Overtime", LpMinimize)

# Decision variables: regular-time and overtime production quantities per product
x_reg = {p: LpVariable(f"x_reg_{p}", lowBound=0) for p in products}
x_ot = {p: LpVariable(f"x_ot_{p}", lowBound=0) for p in products}

# Objective: minimize total cost
# regular_cost[p] = base_profit[p]
# overtime_cost[p] = overtime_cost_multiplier * base_profit[p]
prob += lpSum(base_profit[p] * x_reg[p] + overtime_cost_multiplier * base_profit[p] * x_ot[p] for p in products), "Total_Cost"

# 1) Equipment capacity constraints (regular + overtime share equipment hours)
for equip in equipment_names:
    prob += (
        lpSum(processing_times[(equip, p)] * (x_reg[p] + x_ot[p]) for p in products) <= effective_hours[equip],
        f"Equipment_{equip}_capacity_shared"
    )

# 2) Global overtime hours cap across all equipment and products
prob += (
    lpSum(processing_times[(equip, p)] * x_ot[p] for equip in equipment_names for p in products) <= overtime_hours_cap,
    "Global_Overtime_Hours_Cap"
)

# 3) Minimum production requirements for each product
for p in products:
    prob += (
        x_reg[p] + x_ot[p] >= min_prod[p],
        f"Min_Production_{p}"
    )

# Solve
prob.solve(GUROBI_CMD(msg=0))

# Print results
for p in products:
    print(f"Product {p} regular: {value(x_reg[p]):.6f} units")
    print(f"Product {p} overtime: {value(x_ot[p]):.6f} units")

obj_val = value(prob.objective)
print(f"OBJECTIVE_VALUE: {obj_val}")
