import os
import csv
from itertools import combinations
from math import inf

import gurobi_pulp_compat as pulp


def load_processing_times(filepath):
    processing_times = []
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            times = [int(val) for val in row[1:]]
            processing_times.append(times)
    return processing_times


def load_general_parameters(filepath):
    params = {}
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if len(row) < 2:
                continue
            name = row[0].strip()
            value_str = row[1].strip()
            if value_str == "":
                continue
            try:
                val = float(value_str)
            except ValueError:
                continue
            params[name] = val
    return params


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, '..', 'data')

    proc_path = os.path.join(data_dir, 'table_1.csv')
    gen_path = os.path.join(data_dir, 'general_parameters.csv')

    processing_times = load_processing_times(proc_path)
    params = load_general_parameters(gen_path)

    n_products = len(processing_times)
    n_machines = len(processing_times[0])

    # Index sets
    products = list(range(n_products))  # 0..2
    machines = list(range(n_machines))  # 0..2

    # Extract parameters
    time_window = {
        0: params['time_window_1'],
        1: params['time_window_2'],
        2: params['time_window_3'],
    }
    overtime_window = {
        0: params['overtime_window_1'],
        1: params['overtime_window_2'],
        2: params['overtime_window_3'],
    }
    overtime_penalty = params['overtime_penalty_per_unit']
    machine1_review_threshold = params['machine1_overtime_review_threshold']
    machine1_review_fee = params['machine1_overtime_review_fee']
    M = {
        0: params['M_1'],
        1: params['M_2'],
        2: params['M_3'],
    }

    # Compute busy times B_j = sum_i t_ij (constants)
    busy_time = {}
    for j in machines:
        busy_time[j] = sum(processing_times[i][j] for i in products)

    # Define MILP model
    model = pulp.LpProblem('FlowShop_with_Overtime', pulp.LpMinimize)

    # Decision variables
    # Start times S_{i,j} >= 0
    S = pulp.LpVariable.dicts('S', (products, machines), lowBound=0, cat=pulp.LpContinuous)

    # Binary precedence y_{i,k} for i<k: 1 if i before k
    pairs = list(combinations(products, 2))
    y = pulp.LpVariable.dicts('y', pairs, lowBound=0, upBound=1, cat=pulp.LpBinary)

    # Makespan T
    T = pulp.LpVariable('T', lowBound=0, cat=pulp.LpContinuous)

    # Overtime used on each machine j
    overtime_used = pulp.LpVariable.dicts('overtime_used', machines, lowBound=0, cat=pulp.LpContinuous)
    machine1_review = pulp.LpVariable('machine1_overtime_review', cat=pulp.LpBinary)

    # Constraints

    # 1. Non-overlap on each machine using common precedence y_{i,k}
    for (i, k) in pairs:
        for j in machines:
            t_ij = processing_times[i][j]
            t_kj = processing_times[k][j]
            Mj = M[j]
            # If y_{i,k} = 1 then i before k on machine j
            model += S[i][j] + t_ij <= S[k][j] + Mj * (1 - y[(i, k)])
            # If y_{i,k} = 0 then k before i on machine j
            model += S[k][j] + t_kj <= S[i][j] + Mj * y[(i, k)]

    # 2. Technological precedence within each product
    # Machine order: 0 -> 1 -> 2 (1->2->3 in original)
    for i in products:
        # S_{i,2} >= S_{i,1} + t_i1
        model += S[i][1] >= S[i][0] + processing_times[i][0]
        # S_{i,3} >= S_{i,2} + t_i2
        model += S[i][2] >= S[i][1] + processing_times[i][1]

    # 3. Makespan definition: T >= C_{i,3}
    for i in products:
        model += T >= S[i][2] + processing_times[i][2]

    # 4. Maintenance-related availability and overtime
    for j in machines:
        Bj = busy_time[j]
        # B_j <= time_window_j + overtime_used_j
        model += Bj <= time_window[j] + overtime_used[j]
        # overtime_used_j <= overtime_window_j
        model += overtime_used[j] <= overtime_window[j]
    model += overtime_used[0] <= machine1_review_threshold + overtime_window[0] * machine1_review

    # Objective: minimize T + overtime_penalty * sum_j overtime_used_j
    model += T + overtime_penalty * pulp.lpSum(overtime_used[j] for j in machines) + machine1_review_fee * machine1_review

    # Solve with Gurobi
    solver = pulp.GUROBI_CMD(msg=False)
    result_status = model.solve(solver)

    if pulp.LpStatus[result_status] != 'Optimal':
        raise RuntimeError(f'Solver did not find optimal solution, status: {pulp.LpStatus[result_status]}')

    obj_val = pulp.value(model.objective)
    print(f'OBJECTIVE_VALUE: {obj_val}')


if __name__ == '__main__':
    main()
