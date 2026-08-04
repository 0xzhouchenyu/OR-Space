import os
import csv
from gurobi_pulp_compat import *

def main():
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    
    # Load food items
    items = []
    with open(os.path.join(base_dir, 'table_1.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            items.append({
                'name': row['Item'].strip(),
                'protein': float(row['Protein_Content_per_100g'].strip()),
                'cost': float(row['Cost_per_100g'].strip()),
                'type': row['Type'].strip()
            })
    
    # Load parameters
    params = {}
    with open(os.path.join(base_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name'].strip()] = float(row['Value'].strip())
    
    min_veg_types = int(params['min_vegetable_types'])
    max_budget = params['max_budget']
    total_weight = params['total_weight_limit']
    
    max_units = int(total_weight // 100)  # max 100g units per item
    
    prob = LpProblem("dinner", LpMaximize)
    
    # x[i] = number of 100g units of item i
    x = {i: LpVariable(f"x_{items[i]['name']}", lowBound=0, cat='Integer') for i in range(len(items))}
    # y[i] = binary, whether item i is selected
    y = {i: LpVariable(f"y_{items[i]['name']}", cat='Binary') for i in range(len(items))}
    
    prob += lpSum(items[i]['protein'] * x[i] for i in range(len(items)))
    prob += lpSum(items[i]['cost'] * x[i] for i in range(len(items))) <= max_budget
    prob += lpSum(100 * x[i] for i in range(len(items))) <= total_weight
    
    for i in range(len(items)):
        prob += x[i] <= max_units * y[i]
        prob += x[i] >= y[i]  # if selected, at least 100g
    
    veg_indices = [i for i in range(len(items)) if items[i]['type'] == 'Vegetable']
    prob += lpSum(y[i] for i in veg_indices) >= min_veg_types
    
    prob.solve(GUROBI_CMD(msg=0))
    
    obj = value(prob.objective)
    for i in range(len(items)):
        if value(x[i]) > 0:
            print(f"{items[i]['name']}: {value(x[i])*100}g, protein={items[i]['protein']*value(x[i])}g, cost=${items[i]['cost']*value(x[i])}")
    
    print(f"OBJECTIVE_VALUE: {obj}")

main()