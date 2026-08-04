import os
import math
import pandas as pd
from gurobi_pulp_compat import LpProblem, LpMinimize, LpVariable, lpSum, LpBinary, GUROBI_CMD, value


def calculate_distance(c1, c2):
    return math.hypot(c1[0] - c2[0], c1[1] - c2[1])


def solve():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, '..', 'data')

    customers = pd.read_csv(os.path.join(data_dir, 'table_1.csv'))
    params_df = pd.read_csv(os.path.join(data_dir, 'general_parameters.csv'))
    params = dict(zip(params_df['Parameter_Name'], params_df['Value']))

    truck_capacity = float(params['truck_capacity'])
    inhouse_truck_limit = int(float(params['inhouse_truck_limit']))
    depot_tw_start = float(params['depot_time_window_start'])
    depot_tw_end = float(params['depot_time_window_end'])
    depot_str = str(params['depot_coordinates']).strip().strip('()')
    depot_x, depot_y = map(float, depot_str.split(','))

    customers['Customer_ID'] = customers['Customer_ID'].astype(int)
    customers['Mandatory_External'] = customers['Mandatory_External'].astype(int)

    active_df = customers[customers['Mandatory_External'] == 0].copy()
    active_ids = active_df['Customer_ID'].tolist()

    coords = {0: (depot_x, depot_y)}
    demand = {0: 0.0}
    tw_start = {0: depot_tw_start}
    tw_end = {0: depot_tw_end}
    service = {0: 0.0}
    outsource_cost = {}
    mandatory_external = {}

    for _, row in customers.iterrows():
        i = int(row['Customer_ID'])
        coords[i] = (float(row['Coordinates_X']), float(row['Coordinates_Y']))
        demand[i] = float(row['Demand'])
        tw_start[i] = float(row['Time_Window_Start'])
        tw_end[i] = float(row['Time_Window_End'])
        service[i] = float(row['Service_Duration'])
        outsource_cost[i] = float(row['Outsource_Cost'])
        mandatory_external[i] = int(row['Mandatory_External'])

    V = [0] + active_ids
    A = [(i, j) for i in V for j in V if i != j]
    A_set = set(A)
    dist = {(i, j): calculate_distance(coords[i], coords[j]) for (i, j) in A}

    prob = LpProblem('VRPHTW_LEZ_Outsourcing', LpMinimize)

    x = LpVariable.dicts('x', A, cat=LpBinary)
    y = LpVariable.dicts('y', active_ids, cat=LpBinary)
    t = LpVariable.dicts('t', V, lowBound=0)
    u = LpVariable.dicts('u', V, lowBound=0)
    z_force = {i: 1 for i in customers.loc[customers['Mandatory_External'] == 1, 'Customer_ID'].astype(int).tolist()}

    prob += (
        lpSum(dist[i, j] * x[i, j] for (i, j) in A) +
        lpSum(outsource_cost[i] * y[i] for i in active_ids) +
        lpSum(outsource_cost[i] * z_force[i] for i in z_force)
    )

    prob += lpSum(x[0, j] for j in active_ids if (0, j) in A_set) <= inhouse_truck_limit
    prob += lpSum(x[i, 0] for i in active_ids if (i, 0) in A_set) <= inhouse_truck_limit

    for j in active_ids:
        prob += lpSum(x[i, j] for i in V if i != j and (i, j) in A_set) == 1 - y[j]
        prob += lpSum(x[j, k] for k in V if k != j and (j, k) in A_set) == 1 - y[j]
        prob += y[j] <= 1

    prob += lpSum(1 for _ in z_force) == len(z_force)

    for i in V:
        prob += t[i] >= tw_start[i]
        prob += t[i] <= tw_end[i]

    M = depot_tw_end + max(service.values()) + max(calculate_distance(coords[i], coords[j]) for i in coords for j in coords if i != j)

    for (i, j) in A:
        if j != 0:
            prob += t[j] >= t[i] + service[i] + dist[i, j] - M * (1 - x[i, j])

    for i in active_ids:
        prob += u[i] >= demand[i]
        prob += u[i] <= truck_capacity * (1 - y[i])

    for (i, j) in A:
        if i != 0 and j != 0:
            prob += u[j] >= u[i] + demand[j] - truck_capacity * (1 - x[i, j])

    solver = GUROBI_CMD(msg=False)
    prob.solve(solver)
    obj = value(prob.objective)
    print(f'OBJECTIVE_VALUE: {obj:.2f}')


if __name__ == '__main__':
    solve()
