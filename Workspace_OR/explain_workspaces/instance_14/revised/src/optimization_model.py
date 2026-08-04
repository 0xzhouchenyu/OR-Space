import os
import csv
from math import floor
from gurobi_pulp_compat import *


def main():
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

    items = []
    with open(os.path.join(base_dir, 'table_1.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            items.append({
                'name': row['Item'].strip(),
                'protein': float(row['Protein_Content_per_100g'].strip()),
                'cost': float(row['Cost_per_100g'].strip()),
                'type': row['Type'].strip(),
                'calories': float(row['Calories_per_100g'].strip()),
                'sodium': float(row['Sodium_mg_per_100g'].strip())
            })

    params = {}
    with open(os.path.join(base_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name'].strip()] = float(row['Value'].strip())

    min_veg_types = int(params['min_vegetable_types'])
    max_budget = params['max_budget']
    total_weight_limit = params['total_weight_limit']
    min_daily_calories = params['min_daily_calories']
    max_daily_calories = params['max_daily_calories']
    max_daily_sodium = params['max_daily_sodium']

    n_items = len(items)
    max_units = int(floor(total_weight_limit / 100.0))
    max_meal_units = 3

    prob = LpProblem('daily_meals', LpMaximize)

    purchase_units = {i: LpVariable(f"purchase_{i}", lowBound=0, cat='Integer') for i in range(n_items)}
    lunch_units = {i: LpVariable(f"lunch_{i}", lowBound=0, cat='Integer') for i in range(n_items)}
    dinner_units = {i: LpVariable(f"dinner_{i}", lowBound=0, cat='Integer') for i in range(n_items)}
    select_item = {i: LpVariable(f"select_{i}", cat='Binary') for i in range(n_items)}

    veg_indices = [i for i in range(n_items) if items[i]['type'] == 'Vegetable']
    lunch_veg_selected = {i: LpVariable(f"lveg_{i}", cat='Binary') for i in veg_indices}
    dinner_veg_selected = {i: LpVariable(f"dveg_{i}", cat='Binary') for i in veg_indices}

    prob += lpSum(items[i]['protein'] * (lunch_units[i] + dinner_units[i]) for i in range(n_items))

    prob += lpSum(items[i]['cost'] * purchase_units[i] for i in range(n_items)) <= max_budget
    prob += 100 * lpSum(purchase_units[i] for i in range(n_items)) <= total_weight_limit

    for i in range(n_items):
        prob += purchase_units[i] >= lunch_units[i] + dinner_units[i]
        prob += purchase_units[i] <= max_units * select_item[i]
        prob += lunch_units[i] <= max_meal_units * select_item[i]
        prob += dinner_units[i] <= max_meal_units * select_item[i]

    prob += lpSum(lunch_units[i] for i in range(n_items)) == 3
    prob += lpSum(dinner_units[i] for i in range(n_items)) == 3

    total_calories = lpSum(items[i]['calories'] * (lunch_units[i] + dinner_units[i]) for i in range(n_items))
    prob += total_calories >= min_daily_calories
    prob += total_calories <= max_daily_calories

    total_sodium = lpSum(items[i]['sodium'] * (lunch_units[i] + dinner_units[i]) for i in range(n_items))
    prob += total_sodium <= max_daily_sodium

    for i in veg_indices:
        prob += lunch_units[i] >= lunch_veg_selected[i]
        prob += lunch_units[i] <= max_meal_units * lunch_veg_selected[i]
        prob += dinner_units[i] >= dinner_veg_selected[i]
        prob += dinner_units[i] <= max_meal_units * dinner_veg_selected[i]

    prob += lpSum(lunch_veg_selected[i] for i in veg_indices) >= min_veg_types
    prob += lpSum(dinner_veg_selected[i] for i in veg_indices) >= min_veg_types

    prob.solve(GUROBI_CMD(msg=0))

    obj = value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj}")


if __name__ == '__main__':
    main()
