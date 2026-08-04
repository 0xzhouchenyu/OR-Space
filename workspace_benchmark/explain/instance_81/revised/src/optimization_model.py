import os
import sys
import pandas as pd
from gurobi_pulp_compat import LpProblem, LpMinimize, LpVariable, lpSum, LpBinary, GUROBI_CMD, value


def load_car_data(data_dir):
    df = pd.read_csv(os.path.join(data_dir, 'table_1.csv'))
    return {int(row['i']): float(row['lambda_i']) for _, row in df.iterrows()}


def load_parameters(data_dir):
    df = pd.read_csv(os.path.join(data_dir, 'general_parameters.csv'))
    params = {}
    for _, row in df.iterrows():
        params[str(row['Parameter_Name'])] = float(row['Value'])
    return params


def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    cars = load_car_data(data_dir)
    params = load_parameters(data_dir)

    car_ids = sorted(cars.keys())
    sides = [1, 2]
    max_length_one_side = params['max_length_one_side']
    available_party_side_count = int(params['available_party_side_count'])

    prob = LpProblem('ParkingSingleUsableSide', LpMinimize)

    y = {s: LpVariable(f'y_{s}', cat=LpBinary) for s in sides}
    a = {(i, s): LpVariable(f'a_{i}_{s}', cat=LpBinary) for i in car_ids for s in sides}
    L = {s: LpVariable(f'L_{s}', lowBound=0) for s in sides}
    T = LpVariable('T', lowBound=0)

    prob += T

    prob += lpSum(y[s] for s in sides) == available_party_side_count, 'exactly_one_usable_side'

    for i in car_ids:
        prob += lpSum(a[i, s] for s in sides) == 1, f'assign_car_{i}'

    for i in car_ids:
        for s in sides:
            prob += a[i, s] <= y[s], f'link_assignment_to_side_{i}_{s}'

    for s in sides:
        prob += L[s] == lpSum(cars[i] * a[i, s] for i in car_ids), f'def_length_{s}'
        prob += L[s] <= max_length_one_side * y[s], f'cap_side_{s}'
        prob += T >= L[s], f'max_side_length_{s}'

    prob.solve(GUROBI_CMD(msg=0))

    obj_val = float(value(prob.objective))
    print(f'OBJECTIVE_VALUE: {obj_val}')


if __name__ == '__main__':
    main()
