import os
import csv
from gurobi_pulp_compat import *


def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

    # Read product data
    products = []
    with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            products.append({
                'name': row['Product Name'].strip(),
                'labor': float(row['Labor per unit'].strip()),
                'material': float(row['Material per unit'].strip()),
                'price': float(row['Selling Price'].strip()),
                'var_cost': float(row['Variable Cost'].strip())
            })

    # Read general parameters
    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name'].strip()] = float(row['Value'].strip())

    available_labor = params['available_labor']
    available_material = params['available_material']

    fixed_cost_shirts = params['fixed_cost_shirts']
    fixed_cost_short_sleeves = params['fixed_cost_short_sleeves']
    fixed_cost_casual_clothes = params['fixed_cost_casual_clothes']

    segment_regular_discount = params['segment_regular_discount']
    segment_promo_discount = params['segment_promo_discount']
    promo_labor_cap = params['segment_promo_labor_cap']
    promo_material_cap = params['segment_promo_material_cap']

    min_batch_shirts = params['min_batch_shirts']
    min_batch_short_sleeves = params['min_batch_short_sleeves']
    min_batch_casual_clothes = params['min_batch_casual_clothes']

    max_prod_shirts = params['max_prod_shirts']
    max_prod_short_sleeves = params['max_prod_short_sleeves']
    max_prod_casual_clothes = params['max_prod_casual_clothes']

    # Map product names to indices and parameters
    n = len(products)
    name_to_index = {p['name']: i for i, p in enumerate(products)}

    # Fixed costs per product index
    fixed_costs = [0.0] * n
    fixed_costs[name_to_index['Shirt']] = fixed_cost_shirts
    fixed_costs[name_to_index['Short-sleeve']] = fixed_cost_short_sleeves
    fixed_costs[name_to_index['Casual Cloth']] = fixed_cost_casual_clothes

    # Min batch per product index
    min_batch = [0.0] * n
    min_batch[name_to_index['Shirt']] = min_batch_shirts
    min_batch[name_to_index['Short-sleeve']] = min_batch_short_sleeves
    min_batch[name_to_index['Casual Cloth']] = min_batch_casual_clothes

    # Max production (big-M) per product index
    max_prod = [0.0] * n
    max_prod[name_to_index['Shirt']] = max_prod_shirts
    max_prod[name_to_index['Short-sleeve']] = max_prod_short_sleeves
    max_prod[name_to_index['Casual Cloth']] = max_prod_casual_clothes

    # Indices for segments
    SEG_REG = 0
    SEG_PRO = 1
    segments = [SEG_REG, SEG_PRO]

    prob = LpProblem("clothing_production_segmented", LpMaximize)

    # Decision variables: q[i][seg] and activation y[i]
    q = [[LpVariable(f"q_{i}_{seg}", lowBound=0, cat='Integer') for seg in segments] for i in range(n)]
    y = [LpVariable(f"y_{i}", lowBound=0, upBound=1, cat='Binary') for i in range(n)]

    # Objective function
    # Effective prices by segment
    unit_profit = [[0.0 for _ in segments] for _ in range(n)]
    for i in range(n):
        base_price = products[i]['price']
        var_cost = products[i]['var_cost']
        # regular segment
        eff_price_reg = segment_regular_discount * base_price
        # promo segment
        eff_price_pro = segment_promo_discount * base_price
        unit_profit[i][SEG_REG] = eff_price_reg - var_cost
        unit_profit[i][SEG_PRO] = eff_price_pro - var_cost

    profit_terms = []
    for i in range(n):
        for seg in segments:
            profit_terms.append(unit_profit[i][seg] * q[i][seg])

    # Activation fixed costs
    fixed_terms = []
    for i in range(n):
        fixed_terms.append(fixed_costs[i] * y[i])

    prob += lpSum(profit_terms) - lpSum(fixed_terms)

    # Capacity constraints (overall labor and material)
    prob += (
        lpSum(products[i]['labor'] * q[i][seg] for i in range(n) for seg in segments)
        <= available_labor
    ), "labor_capacity"

    prob += (
        lpSum(products[i]['material'] * q[i][seg] for i in range(n) for seg in segments)
        <= available_material
    ), "material_capacity"

    # Promotional segment specific capacities
    prob += (
        lpSum(products[i]['labor'] * q[i][SEG_PRO] for i in range(n))
        <= promo_labor_cap
    ), "promo_labor_capacity"

    prob += (
        lpSum(products[i]['material'] * q[i][SEG_PRO] for i in range(n))
        <= promo_material_cap
    ), "promo_material_capacity"

    # Activation big-M linking and minimum batch constraints
    for i in range(n):
        # q[i][seg] <= max_prod[i] * y[i]
        prob += q[i][SEG_REG] <= max_prod[i] * y[i], f"max_reg_prod_link_{i}"
        prob += q[i][SEG_PRO] <= max_prod[i] * y[i], f"max_pro_prod_link_{i}"

        # total production >= min_batch[i] * y[i]
        prob += (
            q[i][SEG_REG] + q[i][SEG_PRO] >= min_batch[i] * y[i]
        ), f"min_batch_{i}"

    # Solve problem
    prob.solve(GUROBI_CMD(msg=0))

    obj_val = value(prob.objective)

    # Print detailed production plan
    for i in range(n):
        reg_val = value(q[i][SEG_REG])
        pro_val = value(q[i][SEG_PRO])
        y_val = value(y[i])
        print(f"{products[i]['name']} - regular: {reg_val}, promo: {pro_val}, activated: {y_val}")

    print(f"OBJECTIVE_VALUE: {obj_val}")


if __name__ == "__main__":
    main()
