import os
import csv
from gurobi_pulp_compat import *

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, '..', 'data')
    
    # Read table_1.csv
    workshops = []
    capacities = {}
    rates = {}  # rates[(workshop, component)] = production rate
    
    filepath = os.path.join(data_dir, 'table_1.csv')
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            w = row['Workshop'].strip()
            workshops.append(w)
            capacities[w] = float(row['Production_Capacity_hours'].strip())
            rates[(w, 1)] = float(row['Production_Rate_Component_1_units_per_hour'].strip())
            rates[(w, 2)] = float(row['Production_Rate_Component_2_units_per_hour'].strip())
            rates[(w, 3)] = float(row['Production_Rate_Component_3_units_per_hour'].strip())
    
    components = [1, 2, 3]
    
    # Create LP problem
    prob = LpProblem("Maximize_Completed_Products", LpMaximize)
    
    # Decision variables: hours each workshop allocates to each component
    x = {}
    for w in workshops:
        for c in components:
            x[(w, c)] = LpVariable(f"x_{w}_{c}", lowBound=0)
    
    # z = number of completed products (min of total units per component)
    z = LpVariable("z", lowBound=0)
    
    # Objective: maximize z
    prob += z, "Maximize_completed_products"
    
    # Capacity constraints: each workshop's total hours <= capacity
    for w in workshops:
        prob += (
            lpSum(x[(w, c)] for c in components) <= capacities[w],
            f"Capacity_{w}"
        )
    
    # z <= total production of each component
    for c in components:
        prob += (
            z <= lpSum(rates[(w, c)] * x[(w, c)] for w in workshops),
            f"Min_component_{c}"
        )
    
    # Solve
    prob.solve(GUROBI_CMD(msg=0))
    
    # Print solution details
    print(f"Status: {LpStatus[prob.status]}")
    for w in workshops:
        for c in components:
            val = value(x[(w, c)])
            if val and val > 1e-6:
                print(f"Workshop {w}, Component {c}: {val:.2f} hours -> {rates[(w,c)] * val:.2f} units")
    
    for c in components:
        total = sum(rates[(w, c)] * value(x[(w, c)]) for w in workshops)
        print(f"Total Component {c}: {total:.2f} units")
    
    obj_val = value(prob.objective)
    print(f"\nOBJECTIVE_VALUE: {obj_val:.1f}")

if __name__ == "__main__":
    main()