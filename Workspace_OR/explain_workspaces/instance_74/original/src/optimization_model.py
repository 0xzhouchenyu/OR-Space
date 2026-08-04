import os
import csv
from gurobi_pulp_compat import *

def solve():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv')) as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name'].strip()] = float(row['Value'].strip())

    precedences = []
    with open(os.path.join(data_dir, 'table_1.csv')) as f:
        reader = csv.DictReader(f)
        for row in reader:
            precedences.append((row['Predecessor'].strip(), row['Successor'].strip()))

    activities = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
    dur = {a: int(params[f'activity_{a}_duration']) for a in activities}
    work_cost = params['work_cost_per_day']
    machine_cost = params['machine_rental_cost_per_day']

    prob = LpProblem("Project_Cost_Minimization", LpMinimize)

    S = {a: LpVariable(f'S_{a}', lowBound=0) for a in activities}
    T = LpVariable('T', lowBound=0)

    prob += work_cost * T + machine_cost * (S['B'] + dur['B'] - S['A'])

    for pred, succ in precedences:
        prob += S[succ] >= S[pred] + dur[pred]

    prob += T >= S['C'] + dur['C']
    prob += T >= S['B'] + dur['B']

    prob.solve(GUROBI_CMD(msg=0))

    print(f"OBJECTIVE_VALUE: {value(prob.objective)}")

solve()
