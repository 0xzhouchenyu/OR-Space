import os
from utils import load_general_parameters
import gurobi_pulp_compat as pulp

# Load data
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
params = load_general_parameters(os.path.join(data_dir, 'general_parameters.csv'))

# Extract parameters
sell_price_table = params['sell_price_table']
sell_price_chair = params['sell_price_chair']
sell_price_bookshelf = params['sell_price_bookshelf']

cost_table = params['manufacturing_cost_table']
cost_chair = params['manufacturing_cost_chair']
cost_bookshelf = params['manufacturing_cost_bookshelf']

space_table = params['warehouse_space_table']
space_chair = params['warehouse_space_chair']
space_bookshelf = params['warehouse_space_bookshelf']

max_warehouse = params['max_warehouse_space']
min_tables = params['min_tables']
min_bookshelves = params['min_bookshelves']
max_total = params['max_total_items']

# Profit per item
profit_table = sell_price_table - cost_table        # 80
profit_chair = sell_price_chair - cost_chair          # 30
profit_bookshelf = sell_price_bookshelf - cost_bookshelf  # 60

# Create the LP problem
prob = pulp.LpProblem("Furniture_Production", pulp.LpMaximize)

# Decision variables (integer, non-negative)
x_tables = pulp.LpVariable("tables", lowBound=0, cat='Integer')
x_chairs = pulp.LpVariable("chairs", lowBound=0, cat='Integer')
x_bookshelves = pulp.LpVariable("bookshelves", lowBound=0, cat='Integer')

# Objective: maximize profit
prob += profit_table * x_tables + profit_chair * x_chairs + profit_bookshelf * x_bookshelves, "Total_Profit"

# Constraints
# Warehouse space constraint
prob += space_table * x_tables + space_chair * x_chairs + space_bookshelf * x_bookshelves <= max_warehouse, "Warehouse_Space"

# Minimum production requirements
prob += x_tables >= min_tables, "Min_Tables"
prob += x_bookshelves >= min_bookshelves, "Min_Bookshelves"

# Maximum total production
prob += x_tables + x_chairs + x_bookshelves <= max_total, "Max_Total_Items"

# Solve
prob.solve(pulp.GUROBI_CMD(msg=0))

# Output results
print(f"Status: {pulp.LpStatus[prob.status]}")
print(f"Tables: {int(x_tables.varValue)}")
print(f"Chairs: {int(x_chairs.varValue)}")
print(f"Bookshelves: {int(x_bookshelves.varValue)}")

obj_val = pulp.value(prob.objective)
print(f"OBJECTIVE_VALUE: {obj_val}")