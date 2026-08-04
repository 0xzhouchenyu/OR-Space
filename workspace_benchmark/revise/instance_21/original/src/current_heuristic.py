import os
import csv
from gurobi_pulp_compat import *

def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    
    # Parse general parameters
    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name'].strip()] = float(row['Value'].strip())
    
    cost_a = params['cost_supplier_a']       # 120 USD per table
    cost_b = params['cost_supplier_b']       # 110 USD per table
    cost_c = params['cost_supplier_c']       # 100 USD per table
    size_a = int(params['order_size_supplier_a'])  # 20 tables per order
    size_b = int(params['order_size_supplier_b'])  # 15 tables per order
    size_c = int(params['order_size_supplier_c'])  # 15 tables per order
    min_tables = int(params['min_tables_required'])  # 150
    max_tables = int(params['max_tables_allowed'])   # 600
    min_b_if_a = int(params['min_tables_supplier_b_if_a'])  # 30 tables from B if A is used
    b_requires_c = int(params['supplier_b_requires_c'])      # 1 (boolean)
    
    M = 1000  # Big-M
    
    prob = LpProblem("Restaurant_Tables", LpMinimize)
    
    # Decision variables: number of orders from each supplier (integer >= 0)
    x_a = LpVariable("orders_a", lowBound=0, cat='Integer')
    x_b = LpVariable("orders_b", lowBound=0, cat='Integer')
    x_c = LpVariable("orders_c", lowBound=0, cat='Integer')
    
    # Binary variables for conditional constraints
    y_a = LpVariable("y_a", cat='Binary')  # 1 if ordering from A
    y_b = LpVariable("y_b", cat='Binary')  # 1 if ordering from B
    
    # Objective: minimize total cost (cost per table * number of tables)
    prob += cost_a * size_a * x_a + cost_b * size_b * x_b + cost_c * size_c * x_c
    
    # Total tables constraints
    prob += size_a * x_a + size_b * x_b + size_c * x_c >= min_tables
    prob += size_a * x_a + size_b * x_b + size_c * x_c <= max_tables
    
    # Link binary variables to order variables
    prob += x_a <= M * y_a
    prob += x_a >= y_a
    prob += x_b <= M * y_b
    prob += x_b >= y_b
    
    # If ordering from A, then tables from B >= 30
    prob += size_b * x_b >= min_b_if_a * y_a
    
    # If ordering from B, must order from C
    if b_requires_c:
        prob += x_c >= y_b
    
    prob.solve(GUROBI_CMD(msg=0))
    
    obj_val = value(prob.objective)
    print(f"Orders from A: {value(x_a)}, Tables: {value(x_a)*size_a}")
    print(f"Orders from B: {value(x_b)}, Tables: {value(x_b)*size_b}")
    print(f"Orders from C: {value(x_c)}, Tables: {value(x_c)*size_c}")
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()