import os
import csv
from gurobi_pulp_compat import *

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, '..', 'data')

    # Load container data
    containers = []
    with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            containers.append({
                'code': int(row['Container_Type_Code']),
                'volume': int(row['Volume_cm3']),
                'demand': int(row['Market_Demand_units']),
                'cost': float(row['Unit_Variable_Production_Cost_Yuan_per_unit'])
            })

    # Load general parameters
    fixed_cost = None
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Parameter_Name'].strip() == 'fixed_setup_cost':
                fixed_cost = float(row['Value'])

    n = len(containers)
    
    # Create the problem
    prob = LpProblem("PlasticContainers", LpMinimize)

    # Binary setup variables
    y = {i: LpVariable(f"y_{i}", cat='Binary') for i in range(n)}

    # x[i][j] = units of type i produced to fulfill demand of type j
    # Only allowed if volume[i] >= volume[j] (type i can substitute for type j)
    x = {}
    for i in range(n):
        for j in range(n):
            if containers[i]['volume'] >= containers[j]['volume']:
                x[i, j] = LpVariable(f"x_{i}_{j}", lowBound=0, cat='Integer')

    # Objective: minimize variable costs + fixed setup costs
    prob += (
        lpSum(containers[i]['cost'] * x[i, j] for (i, j) in x) +
        lpSum(fixed_cost * y[i] for i in range(n))
    )

    # Demand constraints: for each type j, total supplied >= demand[j]
    for j in range(n):
        prob += (
            lpSum(x[i, j] for i in range(n) if (i, j) in x) >= containers[j]['demand'],
            f"demand_{j}"
        )

    # Linking constraints: if we produce type i, y[i] must be 1
    # Big M = sum of all demands (upper bound on total production of any type)
    M = sum(c['demand'] for c in containers)
    for i in range(n):
        total_produced_i = lpSum(x[i, j] for j in range(n) if (i, j) in x)
        prob += (
            total_produced_i <= M * y[i],
            f"setup_{i}"
        )

    # Solve
    prob.solve(GUROBI_CMD(msg=0))

    obj_val = value(prob.objective)
    
    # Print solution details
    for i in range(n):
        total_prod = sum(value(x[i, j]) for j in range(n) if (i, j) in x)
        if total_prod > 0:
            print(f"Container type {containers[i]['code']}: produce {total_prod}, setup={'Yes' if value(y[i])>0.5 else 'No'}")

    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()