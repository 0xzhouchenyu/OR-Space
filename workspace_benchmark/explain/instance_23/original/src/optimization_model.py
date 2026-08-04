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
    fixed_costs = [params['fixed_cost_shirts'], params['fixed_cost_short_sleeves'], params['fixed_cost_casual_clothes']]
    
    # Model with integer production quantities and all fixed costs always deducted
    prob = LpProblem("clothing_production", LpMaximize)
    
    n = len(products)
    x = [LpVariable(f"x_{i}", lowBound=0, cat='Integer') for i in range(n)]
    
    # Profit = sum of (price - variable_cost) * x_i - sum of fixed_costs
    unit_profit = [p['price'] - p['var_cost'] for p in products]
    
    # Objective: maximize profit (always deduct all fixed costs since equipment exists)
    total_fixed = sum(fixed_costs)
    prob += lpSum(unit_profit[i] * x[i] for i in range(n)) - total_fixed
    
    # Constraints
    prob += lpSum(products[i]['labor'] * x[i] for i in range(n)) <= available_labor, "labor"
    prob += lpSum(products[i]['material'] * x[i] for i in range(n)) <= available_material, "material"
    
    prob.solve(GUROBI_CMD(msg=0))
    
    obj_val = value(prob.objective)
    
    for i in range(n):
        print(f"{products[i]['name']}: {value(x[i])}")
    
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()