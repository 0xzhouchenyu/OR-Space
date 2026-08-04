import os
import gurobi_pulp_compat as pulp
from utils import load_general_parameters

# Load data
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
params = load_general_parameters(os.path.join(data_dir, 'general_parameters.csv'))

# Extract parameters
shirts_inventory = params['shirts_inventory']
pants_inventory = params['pants_inventory']
price_a = params['package_a_price']
price_b = params['package_b_price']
min_a = params['package_a_min_sales']
min_b = params['package_b_min_sales']
shirts_a = params['package_a_shirts']
pants_a = params['package_a_pants']
shirts_b = params['package_b_shirts']
pants_b = params['package_b_pants']

# Create the LP problem
prob = pulp.LpProblem("Maximize_Revenue", pulp.LpMaximize)

# Decision variables (integer, since we're selling whole packages)
x_a = pulp.LpVariable("Package_A", lowBound=0, cat='Integer')
x_b = pulp.LpVariable("Package_B", lowBound=0, cat='Integer')

# Objective: maximize revenue
prob += price_a * x_a + price_b * x_b, "Total_Revenue"

# Constraints
# Shirts inventory constraint
prob += shirts_a * x_a + shirts_b * x_b <= shirts_inventory, "Shirts_Inventory"

# Pants inventory constraint
prob += pants_a * x_a + pants_b * x_b <= pants_inventory, "Pants_Inventory"

# Minimum sales requirements
prob += x_a >= min_a, "Min_Package_A"
prob += x_b >= min_b, "Min_Package_B"

# Solve
prob.solve(pulp.GUROBI_CMD(msg=0))

# Output results
print(f"Status: {pulp.LpStatus[prob.status]}")
print(f"Package A: {int(pulp.value(x_a))}")
print(f"Package B: {int(pulp.value(x_b))}")

objective_value = pulp.value(prob.objective)
print(f"OBJECTIVE_VALUE: {objective_value}")