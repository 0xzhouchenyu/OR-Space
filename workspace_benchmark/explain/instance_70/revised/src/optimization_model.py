import os
import csv
import gurobi_pulp_compat as pulp
import pandas as pd


def load_distance_matrix(file_path):
    df = pd.read_csv(file_path)
    cities = [str(c) for c in df.columns[1:]]
    dist = {}
    for _, row in df.iterrows():
        i = str(row.iloc[0])
        for j in cities:
            dist[(i, j)] = float(row[j])
    return cities, dist


def load_general_parameters(file_path):
    df = pd.read_csv(file_path)
    return {str(r['parameter']): str(r['value']) for _, r in df.iterrows()}


def solve_revised_path_tsp():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, '..', 'data')
    dist_file = os.path.join(data_dir, 'table_1.csv')
    param_file = os.path.join(data_dir, 'general_parameters.csv')

    cities, dist = load_distance_matrix(dist_file)
    params = load_general_parameters(param_file)

    start_city = str(params['start_city'])
    end_city = str(params['end_city'])
    prohibited_from = str(params['prohibited_from'])
    prohibited_to = str(params['prohibited_to'])
    inspection_arc_from = str(params['inspection_arc_from'])
    inspection_arc_to = str(params['inspection_arc_to'])
    inspection_stop_cost = float(params['inspection_stop_cost'])

    prob = pulp.LpProblem('Hazmat_Fixed_End_Path_TSP', pulp.LpMinimize)

    x = {}
    for i in cities:
        for j in cities:
            if i != j:
                ub = 0 if (i == prohibited_from and j == prohibited_to) else 1
                x[(i, j)] = pulp.LpVariable(f'x_{i}_{j}', lowBound=0, upBound=ub, cat='Binary')

    pos = {}
    for i in cities:
        pos[i] = pulp.LpVariable(f'pos_{i}', lowBound=1, upBound=len(cities), cat='Continuous')

    prob += pulp.lpSum((dist[(i, j)] + (inspection_stop_cost if i == inspection_arc_from and j == inspection_arc_to else 0.0)) * x[(i, j)] for i in cities for j in cities if i != j)

    for i in cities:
        if i == start_city:
            prob += pulp.lpSum(x[(i, j)] for j in cities if j != i) == 1
            prob += pulp.lpSum(x[(j, i)] for j in cities if j != i) == 0
        elif i == end_city:
            prob += pulp.lpSum(x[(i, j)] for j in cities if j != i) == 0
            prob += pulp.lpSum(x[(j, i)] for j in cities if j != i) == 1
        else:
            prob += pulp.lpSum(x[(i, j)] for j in cities if j != i) == 1
            prob += pulp.lpSum(x[(j, i)] for j in cities if j != i) == 1

    prob += pos[start_city] == 1
    prob += pos[end_city] == len(cities)

    n = len(cities)
    for i in cities:
        for j in cities:
            if i != j:
                prob += pos[j] >= pos[i] + 1 - n * (1 - x[(i, j)])

    solver = pulp.GUROBI_CMD(msg=0)
    prob.solve(solver)

    obj_val = float(pulp.value(prob.objective))
    print(f'OBJECTIVE_VALUE: {obj_val}')


if __name__ == '__main__':
    solve_revised_path_tsp()
