import os
from utils import load_general_parameters
import gurobi_pulp_compat as pulp

# Load data
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
params = load_general_parameters(os.path.join(data_dir, 'general_parameters.csv'))

# Extract parameters
profit_A = params['profit_per_kg_product_A']
profit_B = params['profit_per_kg_product_B']
max_hours_w1 = params['max_production_hours_week_1']
max_hours_w2 = params['max_production_hours_week_2']
hours_A = params['hours_per_kg_product_A']
hours_B = params['hours_per_kg_product_B']
min_ratio_B_to_A = params['min_output_ratio_product_B_to_A']
storage_ratio_A_to_B = params['storage_space_ratio_product_A_to_B']
max_storage_A_eq_w1 = params['max_storage_product_A_equiv_week_1']
max_storage_A_eq_w2 = params['max_storage_product_A_equiv_week_2']
initial_inv_A = params['initial_inventory_A']
initial_inv_B = params['initial_inventory_B']
storage_cost_A = params['storage_cost_per_kg_A']
storage_cost_B = params['storage_cost_per_kg_B']
promo_bonus_A = params['promo_profit_bonus_A']
promo_bonus_B = params['promo_profit_bonus_B']
max_promos_A = params['max_promotions_product_A']
max_promos_B = params['max_promotions_product_B']

weeks = [1, 2]

# Derived storage capacities (in storage-space units)
storage_cap_w1 = max_storage_A_eq_w1 * storage_ratio_A_to_B
storage_cap_w2 = max_storage_A_eq_w2 * storage_ratio_A_to_B

# Create the MILP problem
prob = pulp.LpProblem("Two_Week_Production_Promotion_Planning", pulp.LpMaximize)

# Decision variables
prod_A = {t: pulp.LpVariable(f"prod_A_{t}", lowBound=0) for t in weeks}
prod_B = {t: pulp.LpVariable(f"prod_B_{t}", lowBound=0) for t in weeks}
inv_A = {t: pulp.LpVariable(f"inv_A_{t}", lowBound=0) for t in weeks}
inv_B = {t: pulp.LpVariable(f"inv_B_{t}", lowBound=0) for t in weeks}
sales_A = {t: pulp.LpVariable(f"sales_A_{t}", lowBound=0) for t in weeks}
sales_B = {t: pulp.LpVariable(f"sales_B_{t}", lowBound=0) for t in weeks}
promo_A = {t: pulp.LpVariable(f"promo_A_{t}", lowBound=0, upBound=1, cat="Binary") for t in weeks}
promo_B = {t: pulp.LpVariable(f"promo_B_{t}", lowBound=0, upBound=1, cat="Binary") for t in weeks}

# Auxiliary variables for promotional extra revenue (linearization)
extra_rev_A = {t: pulp.LpVariable(f"extra_rev_A_{t}", lowBound=0) for t in weeks}
extra_rev_B = {t: pulp.LpVariable(f"extra_rev_B_{t}", lowBound=0) for t in weeks}

# Big-M values for linking promo and sales in extra revenue
# Upper bounds on sales from production and storage limits
# Max hours per week = 40, minimal hours per kg among products = 3 -> max total kg per week <= 40/3
max_sales_per_week = max_hours_w1 / min(hours_A, hours_B)
M_A = max_sales_per_week * promo_bonus_A
M_B = max_sales_per_week * promo_bonus_B

# Inventory balance constraints
prob += initial_inv_A + prod_A[1] == sales_A[1] + inv_A[1], "Inv_Balance_A_1"
prob += initial_inv_B + prod_B[1] == sales_B[1] + inv_B[1], "Inv_Balance_B_1"
prob += inv_A[1] + prod_A[2] == sales_A[2] + inv_A[2], "Inv_Balance_A_2"
prob += inv_B[1] + prod_B[2] == sales_B[2] + inv_B[2], "Inv_Balance_B_2"

# Production time constraints
prob += hours_A * prod_A[1] + hours_B * prod_B[1] <= max_hours_w1, "Prod_Hours_1"
prob += hours_A * prod_A[2] + hours_B * prod_B[2] <= max_hours_w2, "Prod_Hours_2"

# Market ratio constraints on sales
prob += sales_B[1] >= min_ratio_B_to_A * sales_A[1], "Market_Ratio_1"
prob += sales_B[2] >= min_ratio_B_to_A * sales_A[2], "Market_Ratio_2"

# Storage capacity constraints on ending inventory
prob += storage_ratio_A_to_B * inv_A[1] + inv_B[1] <= storage_cap_w1, "Storage_Cap_1"
prob += storage_ratio_A_to_B * inv_A[2] + inv_B[2] <= storage_cap_w2, "Storage_Cap_2"

# Promotion count constraints
prob += promo_A[1] + promo_A[2] <= max_promos_A, "Max_Promos_A"
prob += promo_B[1] + promo_B[2] <= max_promos_B, "Max_Promos_B"

# Linearization of promotional extra revenue
for t in weeks:
    # extra_rev_A[t] approximates promo_bonus_A * sales_A[t] * promo_A[t]
    prob += extra_rev_A[t] <= promo_bonus_A * sales_A[t], f"ExtraRevA_le_sales_{t}"
    prob += extra_rev_A[t] <= M_A * promo_A[t], f"ExtraRevA_le_MA_{t}"
    prob += extra_rev_A[t] >= promo_bonus_A * sales_A[t] - M_A * (1 - promo_A[t]), f"ExtraRevA_ge_lb_{t}"

    # extra_rev_B[t] approximates promo_bonus_B * sales_B[t] * promo_B[t]
    prob += extra_rev_B[t] <= promo_bonus_B * sales_B[t], f"ExtraRevB_le_sales_{t}"
    prob += extra_rev_B[t] <= M_B * promo_B[t], f"ExtraRevB_le_MB_{t}"
    prob += extra_rev_B[t] >= promo_bonus_B * sales_B[t] - M_B * (1 - promo_B[t]), f"ExtraRevB_ge_lb_{t}"

# Objective: maximize total profit minus storage cost on week-1 ending inventory
revenue_terms = []
for t in weeks:
    revenue_terms.append(profit_A * sales_A[t] + profit_B * sales_B[t] + extra_rev_A[t] + extra_rev_B[t])

total_revenue = sum(revenue_terms)
storage_cost = storage_cost_A * inv_A[1] + storage_cost_B * inv_B[1]

prob += total_revenue - storage_cost, "Total_Profit_2Weeks"

# Solve
prob.solve(pulp.GUROBI_CMD(msg=0))

obj_val = pulp.value(prob.objective)
print(f"OBJECTIVE_VALUE: {obj_val:.3f}")
