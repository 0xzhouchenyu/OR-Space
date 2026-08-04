import os
from utils import load_general_parameters
import gurobi_pulp_compat as pulp

# Load data
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
params = load_general_parameters(os.path.join(data_dir, 'general_parameters.csv'))

# Extract price and cost parameters
sell_price_table = params['sell_price_table']
sell_price_chair = params['sell_price_chair']
sell_price_bookshelf = params['sell_price_bookshelf']

cost_table = params['manufacturing_cost_table']
cost_chair = params['manufacturing_cost_chair']
cost_bookshelf = params['manufacturing_cost_bookshelf']

# Warehouse space parameters
space_table = params['warehouse_space_table']
space_chair = params['warehouse_space_chair']
space_bookshelf = params['warehouse_space_bookshelf']
max_warehouse = params['max_warehouse_space']

# Minimum production requirements
min_tables = params['min_tables']
min_bookshelves = params['min_bookshelves']

# Maximum total production
max_total = params['max_total_items']

# Labor-hour parameters
labor_table = params['labor_hours_table']
labor_chair = params['labor_hours_chair']
labor_bookshelf = params['labor_hours_bookshelf']
max_labor_regular = params['max_labor_hours_month_regular']
max_labor_rush = params['max_labor_hours_month_rush']

# Rush capacity and bonuses
max_rush_items = params['max_rush_items_month']
rush_bonus_table = params['rush_profit_bonus_table']
rush_bonus_chair = params['rush_profit_bonus_chair']
rush_bonus_bookshelf = params['rush_profit_bonus_bookshelf']

# Profit per item in regular mode
profit_table_regular = sell_price_table - cost_table
profit_chair_regular = sell_price_chair - cost_chair
profit_bookshelf_regular = sell_price_bookshelf - cost_bookshelf

# Profit per item in rush mode (regular profit + rush bonus)
profit_table_rush = profit_table_regular + rush_bonus_table
profit_chair_rush = profit_chair_regular + rush_bonus_chair
profit_bookshelf_rush = profit_bookshelf_regular + rush_bonus_bookshelf

# Create the MILP problem
prob = pulp.LpProblem("Furniture_Production_With_Modes", pulp.LpMaximize)

# Decision variables (integer, non-negative)
# Regular mode
x_tables_reg = pulp.LpVariable("tables_regular", lowBound=0, cat='Integer')
x_chairs_reg = pulp.LpVariable("chairs_regular", lowBound=0, cat='Integer')
x_bookshelves_reg = pulp.LpVariable("bookshelves_regular", lowBound=0, cat='Integer')

# Rush mode
x_tables_rush = pulp.LpVariable("tables_rush", lowBound=0, cat='Integer')
x_chairs_rush = pulp.LpVariable("chairs_rush", lowBound=0, cat='Integer')
x_bookshelves_rush = pulp.LpVariable("bookshelves_rush", lowBound=0, cat='Integer')

# Objective: maximize total profit (regular + rush)
prob += (
    profit_table_regular * x_tables_reg
    + profit_chair_regular * x_chairs_reg
    + profit_bookshelf_regular * x_bookshelves_reg
    + profit_table_rush * x_tables_rush
    + profit_chair_rush * x_chairs_rush
    + profit_bookshelf_rush * x_bookshelves_rush
), "Total_Profit"

# Warehouse space constraint (shared by both modes)
prob += (
    space_table * (x_tables_reg + x_tables_rush)
    + space_chair * (x_chairs_reg + x_chairs_rush)
    + space_bookshelf * (x_bookshelves_reg + x_bookshelves_rush)
    <= max_warehouse
), "Warehouse_Space"

# Regular labor-hours constraint
prob += (
    labor_table * x_tables_reg
    + labor_chair * x_chairs_reg
    + labor_bookshelf * x_bookshelves_reg
    <= max_labor_regular
), "Regular_Labor_Hours"

# Rush labor-hours constraint
prob += (
    labor_table * x_tables_rush
    + labor_chair * x_chairs_rush
    + labor_bookshelf * x_bookshelves_rush
    <= max_labor_rush
), "Rush_Labor_Hours"

# Rush items capacity constraint
prob += (
    x_tables_rush + x_chairs_rush + x_bookshelves_rush
    <= max_rush_items
), "Rush_Items_Cap"

# Minimum production requirements (total over both modes)
prob += x_tables_reg + x_tables_rush >= min_tables, "Min_Tables_Total"
prob += x_bookshelves_reg + x_bookshelves_rush >= min_bookshelves, "Min_Bookshelves_Total"

# Maximum total production over all products and modes
prob += (
    x_tables_reg + x_tables_rush
    + x_chairs_reg + x_chairs_rush
    + x_bookshelves_reg + x_bookshelves_rush
    <= max_total
), "Max_Total_Items_All_Modes"

# Solve using Gurobi
prob.solve(pulp.GUROBI_CMD(msg=0))

# Output results
print(f"Status: {pulp.LpStatus[prob.status]}")
print(f"Tables (regular): {int(x_tables_reg.varValue)}")
print(f"Tables (rush): {int(x_tables_rush.varValue)}")
print(f"Chairs (regular): {int(x_chairs_reg.varValue)}")
print(f"Chairs (rush): {int(x_chairs_rush.varValue)}")
print(f"Bookshelves (regular): {int(x_bookshelves_reg.varValue)}")
print(f"Bookshelves (rush): {int(x_bookshelves_rush.varValue)}")

obj_val = pulp.value(prob.objective)
print(f"OBJECTIVE_VALUE: {obj_val}")
