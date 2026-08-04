import os
import csv
import math
from gurobi_pulp_compat import *

def calculate_distance(c1, c2):
    return math.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)

def solve():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    table_1_path = os.path.join(data_dir, 'table_1.csv')
    params_path = os.path.join(data_dir, 'general_parameters.csv')

    params = {}
    with open(params_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('Parameter_Name'):
                continue
            parts = line.split(',')
            params[parts[0]] = ','.join(parts[1:-2]) if len(parts) > 4 else parts[1]

    num_customers = int(params['num_customers'])
    max_trucks = int(params['max_trucks'])
    truck_capacity = float(params['truck_capacity'])

    depot_str = params.get('depot_coordinates', '(40 50)').strip('()')
    if ',' in depot_str:
        depot_x, depot_y = map(float, depot_str.split(','))
    else:
        depot_x, depot_y = map(float, depot_str.split())

    depot_tw_start = float(params['depot_time_window_start'])
    depot_tw_end = float(params['depot_time_window_end'])

    coords = [(depot_x, depot_y)]
    demands_list = [0]
    tw_list = [(depot_tw_start, depot_tw_end)]
    svc_list = [0]

    with open(table_1_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            coords.append((float(row['Coordinates_X']), float(row['Coordinates_Y'])))
            demands_list.append(float(row['Demand']))
            tw_list.append((float(row['Time_Window_Start']), float(row['Time_Window_End'])))
            svc_list.append(float(row['Service_Duration']))

    n = len(coords)
    N = list(range(1, n))
    V = list(range(n))

    dist = {}
    for i in V:
        for j in V:
            dist[i, j] = calculate_distance(coords[i], coords[j])

    A = []
    for i in V:
        for j in V:
            if i == j:
                continue
            if i != 0 and j != 0:
                if tw_list[i][0] + svc_list[i] + dist[i, j] > tw_list[j][1]:
                    continue
            if i == 0 and j != 0:
                if tw_list[0][0] + dist[0, j] > tw_list[j][1]:
                    continue
            if i != 0 and j == 0:
                if tw_list[i][0] + svc_list[i] + dist[i, 0] > tw_list[0][1]:
                    continue
            A.append((i, j))

    A_set = set(A)

    prob = LpProblem("VRPHTW", LpMinimize)

    x = LpVariable.dicts("x", A, cat='Binary')
    t = LpVariable.dicts("t", V, lowBound=0)

    prob += lpSum(dist[i, j] * x[i, j] for i, j in A)

    prob += lpSum(x[0, j] for j in N if (0, j) in A_set) <= max_trucks

    for i in N:
        prob += lpSum(x[j, i] for j in V if (j, i) in A_set) == 1
        prob += lpSum(x[i, j] for j in V if (i, j) in A_set) == 1

    for i in N:
        prob += t[i] >= tw_list[i][0]
        prob += t[i] <= tw_list[i][1]

    t[0].setInitialValue(0)
    prob += t[0] >= tw_list[0][0]
    prob += t[0] <= tw_list[0][1]

    M_val = tw_list[0][1] + max(svc_list)
    for i, j in A:
        if j != 0:
            prob += t[i] + svc_list[i] + dist[i, j] - t[j] <= M_val * (1 - x[i, j])

    for i, j in A:
        if i != 0 and j != 0:
            prob += demands_list[i] + demands_list[j] <= truck_capacity + truck_capacity * (1 - x[i, j])

    prob.solve(GUROBI_CMD(msg=0, timeLimit=100))

    if prob.status in [1, -1]:
        obj = value(prob.objective)
        if obj is not None:
            print(f"OBJECTIVE_VALUE: {round(obj, 2)}")
        else:
            print("OBJECTIVE_VALUE: None")
    else:
        print("OBJECTIVE_VALUE: None")

solve()
