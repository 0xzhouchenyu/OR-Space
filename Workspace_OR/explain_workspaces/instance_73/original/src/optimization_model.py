import os
import csv
from gurobi_pulp_compat import *

def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    
    # Read general parameters
    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name'].strip()] = row['Value'].strip()
    
    max_children = int(params['max_children_trip'])
    min_children = int(params['min_children_trip'])
    
    # Read table_1 for children and costs
    children = []
    costs = {}
    with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['Child'].strip()
            cost = int(row['Cost'].strip())
            children.append(name)
            costs[name] = cost
    
    # Create the optimization model
    prob = LpProblem("FamilyTrip", LpMinimize)
    
    # Decision variables: binary for each child
    x = {child: LpVariable(f"x_{child}", cat='Binary') for child in children}
    
    # Objective: minimize total cost
    prob += lpSum(costs[child] * x[child] for child in children), "TotalCost"
    
    # Constraint: at least min_children and at most max_children
    prob += lpSum(x[child] for child in children) >= min_children, "MinChildren"
    prob += lpSum(x[child] for child in children) <= max_children, "MaxChildren"
    
    # Bob must be taken
    prob += x['Bob'] == 1, "BobMustGo"
    
    # Alice and Diana cannot both be taken
    prob += x['Alice'] + x['Diana'] <= 1, "AliceDianaConflict"
    
    # Bob and Charlie cannot both be taken
    prob += x['Bob'] + x['Charlie'] <= 1, "BobCharlieConflict"
    
    # Charlie must be accompanied by Diana (if Charlie goes, Diana must go)
    prob += x['Charlie'] <= x['Diana'], "CharlieRequiresDiana"
    
    # Diana must be accompanied by Ella (if Diana goes, Ella must go)
    prob += x['Diana'] <= x['Ella'], "DianaRequiresElla"
    
    # Solve
    prob.solve(GUROBI_CMD(msg=0))
    
    # Print solution details
    print(f"Status: {LpStatus[prob.status]}")
    for child in children:
        if x[child].varValue > 0.5:
            print(f"  {child}: taken (cost={costs[child]})")
    
    obj_val = value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()