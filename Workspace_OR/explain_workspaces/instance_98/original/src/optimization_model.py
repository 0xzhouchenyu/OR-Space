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
            products.append(row)
    
    # Read general parameters
    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name']] = float(row['Value'])
    
    # Create LP problem
    prob = LpProblem("Production_Optimization", LpMaximize)
    
    # Decision variables (continuous, non-negative)
    x = {}
    for p in products:
        x[p['Product']] = LpVariable(f"x_{p['Product']}", lowBound=0)
    
    # Objective: maximize profit (no overtime - labor is a hard constraint)
    prob += lpSum([float(p['Profit_yuan']) * x[p['Product']] for p in products])
    
    # Constraints
    # Steel constraint
    prob += lpSum([float(p['Steel_Required_kg']) * x[p['Product']] for p in products]) <= params['available_steel'], "Steel"
    
    # Aluminum constraint
    prob += lpSum([float(p['Aluminum_Required_kg']) * x[p['Product']] for p in products]) <= params['available_aluminum'], "Aluminum"
    
    # Labor constraint (hard cap)
    prob += lpSum([float(p['Labor_Required_hours']) * x[p['Product']] for p in products]) <= params['available_labor'], "Labor"
    
    # Solve
    prob.solve(GUROBI_CMD(msg=0))
    
    obj_val = value(prob.objective)
    
    for p in products:
        print(f"{p['Product']}: {value(x[p['Product']])}")
    
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()