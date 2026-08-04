import os
import csv
from gurobi_pulp_compat import *

def main():
    # Load data
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    
    # Read costs from table_1.csv
    costs = {}
    with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            costs[row['Child'].strip()] = float(row['Cost'].strip())
    
    # Read general parameters
    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name'].strip()] = row['Value'].strip()
    
    max_children = int(params['max_children'])
    min_children = int(params['min_children'])
    
    children = list(costs.keys())
    
    # Create binary decision variables
    prob = LpProblem("ZhangFamilyTrip", LpMinimize)
    x = {child: LpVariable(f"x_{child}", cat='Binary') for child in children}
    
    # Objective: minimize total cost
    prob += lpSum(costs[child] * x[child] for child in children), "TotalCost"
    
    # Constraint: Ginny must go
    prob += x['Ginny'] == 1, "Ginny_must_go"
    
    # Constraint: at most max_children
    prob += lpSum(x[child] for child in children) <= max_children, "Max_children"
    
    # Constraint: at least min_children
    prob += lpSum(x[child] for child in children) >= min_children, "Min_children"
    
    # If Harry is taken, Fred cannot be taken: x_Harry + x_Fred <= 1
    prob += x['Harry'] + x['Fred'] <= 1, "Harry_no_Fred"
    
    # If Harry is taken, George cannot be taken: x_Harry + x_George <= 1
    prob += x['Harry'] + x['George'] <= 1, "Harry_no_George"
    
    # If George is taken, Fred must also be taken: x_George <= x_Fred
    prob += x['George'] <= x['Fred'], "George_requires_Fred"
    
    # If George is taken, Hermione must also be taken: x_George <= x_Hermione
    prob += x['George'] <= x['Hermione'], "George_requires_Hermione"
    
    # Solve
    prob.solve(GUROBI_CMD(msg=0))
    
    # Print solution details
    for child in children:
        if x[child].varValue > 0.5:
            print(f"{child}: selected (cost={costs[child]})")
    
    obj_val = value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()