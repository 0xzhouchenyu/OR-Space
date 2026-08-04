import os
import csv
from gurobi_pulp_compat import *

def main():
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    
    # Load demand data
    demand = {}
    with open(os.path.join(base_dir, 'table_1.csv'), 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        quarters = [int(h) for h in header[1:]]
        for row in reader:
            product = row[0].strip()
            for j, q in enumerate(quarters):
                demand[(product, q)] = int(row[j+1])
    
    # Load general parameters
    params = {}
    with open(os.path.join(base_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name'].strip()] = float(row['Value'])
    
    products = ['I', 'II', 'III']
    quarters = [1, 2, 3, 4]
    
    init_inv = params['initial_inventory']
    end_inv_req = params['end_inventory_requirement']
    hours_per_quarter = params['production_hours_per_quarter']
    hours_per_unit = {'I': params['product_I_hours_per_unit'],
                      'II': params['product_II_hours_per_unit'],
                      'III': params['product_III_hours_per_unit']}
    delay_penalty = {'I': params['delay_penalty_product_I'],
                     'II': params['delay_penalty_product_II'],
                     'III': params['delay_penalty_product_III']}
    inv_cost = params['inventory_cost_per_unit']
    
    prob = LpProblem("ProductionScheduling", LpMinimize)
    
    # Decision variables: production quantities
    x = {(p, t): LpVariable(f"x_{p}_{t}", lowBound=0, cat='Integer') for p in products for t in quarters}
    
    # Product I cannot be produced in Q2
    x[('I', 2)].upBound = 0
    
    # Inventory variables
    inv = {(p, t): LpVariable(f"inv_{p}_{t}") for p in products for t in quarters}
    inv_pos = {(p, t): LpVariable(f"inv_pos_{p}_{t}", lowBound=0) for p in products for t in quarters}
    inv_neg = {(p, t): LpVariable(f"inv_neg_{p}_{t}", lowBound=0) for p in products for t in quarters}
    
    # Inventory balance constraints
    for p in products:
        # Quarter 1
        prob += inv[(p, 1)] == init_inv + x[(p, 1)] - demand[(p, 1)]
        # Quarters 2-4
        for t in range(2, 5):
            prob += inv[(p, t)] == inv[(p, t-1)] + x[(p, t)] - demand[(p, t)]
    
    # Split inventory into positive and negative parts
    for p in products:
        for t in quarters:
            prob += inv[(p, t)] == inv_pos[(p, t)] - inv_neg[(p, t)]
    
    # End of Q4: inventory must be at least end_inv_req
    for p in products:
        prob += inv[(p, 4)] >= end_inv_req
    
    # Production hours constraint per quarter
    for t in quarters:
        prob += lpSum(hours_per_unit[p] * x[(p, t)] for p in products) <= hours_per_quarter
    
    # Objective: minimize delay penalties + inventory holding costs
    prob += lpSum(delay_penalty[p] * inv_neg[(p, t)] + inv_cost * inv_pos[(p, t)] 
                  for p in products for t in quarters)
    
    prob.solve(GUROBI_CMD(msg=0))
    
    obj_val = value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()