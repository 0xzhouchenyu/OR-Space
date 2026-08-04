import os
import sys
from gurobi_pulp_compat import *

# Add parent directory to path if needed
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from utils import load_table_1

# Load data
data_dir = os.path.join(script_dir, '..', 'data')
products, equipment_names, processing_times, effective_hours, profit = load_table_1(data_dir)

# Create the LP problem
prob = LpProblem("Factory_Production_Optimization", LpMaximize)

# Decision variables: number of units of each product to produce (continuous, >= 0)
x = {p: LpVariable(f"x_{p}", lowBound=0) for p in products}

# Objective: maximize total profit
prob += lpSum(profit[p] * x[p] for p in products), "Total_Profit"

# Constraints: equipment capacity
for equip in equipment_names:
    prob += (
        lpSum(processing_times[(equip, p)] * x[p] for p in products) <= effective_hours[equip],
        f"Equipment_{equip}_capacity"
    )

# Solve
prob.solve(GUROBI_CMD(msg=0))

# Print results
for p in products:
    print(f"Product {p}: {value(x[p]):.6f} units")

obj_val = value(prob.objective)
print(f"OBJECTIVE_VALUE: {obj_val}")