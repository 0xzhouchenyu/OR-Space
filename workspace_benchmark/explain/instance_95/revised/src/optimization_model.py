import os
import csv
from gurobi_pulp_compat import *


def solve():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    weeks_data = []
    with open(os.path.join(data_dir, 'table_1.csv'), 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['Week'] == 'Total':
                continue
            weeks_data.append({
                'week': int(row['Week']),
                'demand': float(row['Demand_1000_boxes']),
                'capacity': float(row['Production_Capacity_1000_boxes']),
                'cost': float(row['Cost_per_1000_boxes_1000_yuan']),
            })
    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            params[row['Parameter_Name']] = float(row['Value'])

    n = len(weeks_data)
    prob = LpProblem('Beverage_Production_Recovery', LpMinimize)
    x = [LpVariable(f'x_{t+1}', lowBound=0) for t in range(n)]
    s = [LpVariable(f's_{t+1}', lowBound=0) for t in range(n)]
    y = [LpVariable(f'y_{t+1}', cat='Binary') for t in range(n)]
    recovery = LpVariable('week3_recovery_loss', cat='Binary')
    week2_microclean = LpVariable('week2_microclean', cat='Binary')

    prob += lpSum(weeks_data[t]['cost'] * x[t] + params['fixed_setup_cost'] * y[t] for t in range(n)) + lpSum(params['storage_cost_per_thousand_boxes'] * s[t] for t in range(n)) + params['week2_microclean_fee'] * week2_microclean
    for t in range(n):
        cap = weeks_data[t]['capacity']
        if weeks_data[t]['week'] == 3:
            cap = cap - params['week3_capacity_loss_after_week2_push'] * recovery
        prob += x[t] <= cap
        prob += x[t] <= weeks_data[t]['capacity'] * y[t]
        if t == 0:
            prob += x[t] - s[t] == weeks_data[t]['demand']
        else:
            prob += s[t-1] + x[t] - s[t] == weeks_data[t]['demand']
    prob += x[1] <= params['week2_push_threshold'] + weeks_data[1]['capacity'] * recovery
    prob += x[1] <= params['week2_microclean_threshold'] + weeks_data[1]['capacity'] * week2_microclean

    prob.solve(GUROBI_CMD(msg=0))
    print(f"OBJECTIVE_VALUE: {value(prob.objective)}")


if __name__ == '__main__':
    solve()
