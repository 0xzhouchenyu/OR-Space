import os
import csv
from gurobi_pulp_compat import *

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, '..', 'data')

    # Load processing costs from table_1.csv
    cost = {}  # cost[(machine, part)] = value
    with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        parts = [int(p) for p in header[1:]]
        for row in reader:
            machine = row[0].strip()
            for j, p in enumerate(parts):
                cost[(machine, p)] = float(row[j + 1])

    # Load general parameters
    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name'].strip()] = float(row['Value'])

    d = {'A': params['d_A'], 'B': params['d_B'], 'C': params['d_C']}
    max_C = int(params['max_parts_on_C'])

    machines = ['A', 'B', 'C']

    # Decision variables
    prob = LpProblem("MachineAssignment", LpMinimize)

    # x[m][p] = 1 if part p is assigned to machine m
    x = {(m, p): LpVariable(f"x_{m}_{p}", cat='Binary') for m in machines for p in parts}

    # y[m] = 1 if machine m is used (any part assigned to it)
    y = {m: LpVariable(f"y_{m}", cat='Binary') for m in machines}

    # Objective: minimize processing costs + setup costs
    prob += (lpSum(cost[(m, p)] * x[(m, p)] for m in machines for p in parts)
             + lpSum(d[m] * y[m] for m in machines))

    # Each part assigned to exactly one machine
    for p in parts:
        prob += lpSum(x[(m, p)] for m in machines) == 1

    # Linking y to x: if any part on machine m, y[m] = 1
    for m in machines:
        for p in parts:
            prob += x[(m, p)] <= y[m]

    # Constraint 2: Parts 1 and 2 - if part1 on A then part2 on B or C, and vice versa
    # This means: x[A,1] + x[A,2] = 1 (exactly one of parts 1,2 is on A)
    # Wait: "if 1 on A then 2 on B or C" AND "if 1 on B or C then 2 on A"
    # This means: part1 on A ↔ part2 not on A, i.e., x[A,1] + x[A,2] = 1
    prob += x[('A', 1)] + x[('A', 2)] == 1

    # Constraint 3: Fixed assignments
    prob += x[('A', 3)] == 1
    prob += x[('B', 4)] == 1
    prob += x[('C', 5)] == 1

    # Constraint 4: At most 3 parts on machine C
    prob += lpSum(x[('C', p)] for p in parts) <= max_C

    # Solve
    prob.solve(GUROBI_CMD(msg=0))

    obj_val = value(prob.objective)
    
    # Print assignments for debugging
    for p in parts:
        for m in machines:
            if value(x[(m, p)]) > 0.5:
                print(f"Part {p} -> Machine {m} (cost={cost[(m,p)]})")
    for m in machines:
        if value(y[m]) > 0.5:
            print(f"Machine {m} used, setup cost={d[m]}")

    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == '__main__':
    main()