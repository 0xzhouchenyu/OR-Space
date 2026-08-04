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
    ot_reduction = params.get('activity_E_overtime_reduction', 0)
    ot_cost = params.get('activity_E_overtime_cost', 0)
    followup_cost = params.get('activity_E_followup_review_cost', 0)

    prob = LpProblem("Project_Cost_Minimization", LpMinimize)

    S = {a: LpVariable(f'S_{a}', lowBound=0) for a in activities}
    T = LpVariable('T', lowBound=0)
    use_ot = LpVariable('use_ot', cat='Binary')

    actual_dur = {a: dur[a] for a in activities}
    actual_dur['E'] = dur['E'] - ot_reduction * use_ot

    prob += work_cost * T + machine_cost * (S['B'] + dur['B'] - S['A']) + (ot_cost + followup_cost) * use_ot

    for pred, succ in precedences:
        prob += S[succ] >= S[pred] + actual_dur[pred]

    prob += T >= S['C'] + actual_dur['C']
    prob += T >= S['B'] + actual_dur['B']

    prob.solve(GUROBI_CMD(msg=0))

    print(f"OBJECTIVE_VALUE: {value(prob.objective)}")

solve()
