import os
import csv
from gurobi_pulp_compat import *

def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    
    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name'].strip()] = float(row['Value'].strip())
    
    cost_a = params['cost_supplier_a']
    cost_b = params['cost_supplier_b']
    cost_c = params['cost_supplier_c']
    size_a = int(params['order_size_supplier_a'])
    size_b = int(params['order_size_supplier_b'])
    size_c = int(params['order_size_supplier_c'])
    min_tables = int(params['min_tables_required'])
    max_tables = int(params['max_tables_allowed'])
    min_b_if_a = int(params['min_tables_supplier_b_if_a'])
    b_requires_c = int(params['supplier_b_requires_c'])
    max_free_c = int(params['max_free_orders_c'])
    penalty_c = params['penalty_per_extra_order_c']
    shared_bc_fee = params['supplier_bc_shared_inbound_fee']
    
    M = 1000
    
    prob = LpProblem("Restaurant_Tables", LpMinimize)
    
    x_a = LpVariable("orders_a", lowBound=0, cat='Integer')
    x_b = LpVariable("orders_b", lowBound=0, cat='Integer')
    x_c = LpVariable("orders_c", lowBound=0, cat='Integer')
    x_c_extra = LpVariable("orders_c_extra", lowBound=0, cat='Integer')
    
    y_a = LpVariable("y_a", cat='Binary')
    y_b = LpVariable("y_b", cat='Binary')
    y_c = LpVariable("y_c", cat='Binary')
    shared_bc = LpVariable("shared_bc_inbound", cat='Binary')
    
    prob += cost_a * size_a * x_a + cost_b * size_b * x_b + cost_c * size_c * x_c + penalty_c * x_c_extra + shared_bc_fee * shared_bc
    
    prob += size_a * x_a + size_b * x_b + size_c * x_c >= min_tables
    prob += size_a * x_a + size_b * x_b + size_c * x_c <= max_tables
    
    prob += x_a <= M * y_a
    prob += x_a >= y_a
    prob += x_b <= M * y_b
    prob += x_b >= y_b
    prob += x_c <= M * y_c
    prob += x_c >= y_c
    
    prob += size_b * x_b >= min_b_if_a * y_a
    
    if b_requires_c:
        prob += x_c >= y_b
        
    prob += x_c_extra >= x_c - max_free_c
    prob += shared_bc >= y_b + y_c - 1
    prob += shared_bc <= y_b
    prob += shared_bc <= y_c
    
    prob.solve(GUROBI_CMD(msg=0))
    
    obj_val = value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == '__main__':
    main()