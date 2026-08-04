import os
import csv
from gurobi_pulp_compat import *


def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            params[row['Parameter_Name']] = float(row['Value'])

    min_A = params['min_raw_material_A']; min_B = params['min_raw_material_B']; min_C = params['min_raw_material_C']
    cap_A_a = params['warehouse_A_truck_capacity_A']; cap_A_b = params['warehouse_A_truck_capacity_B']; cap_A_c = params['warehouse_A_truck_capacity_C']
    cap_B_a = params['warehouse_B_truck_capacity_A']; cap_B_b = params['warehouse_B_truck_capacity_B']; cap_B_c = params['warehouse_B_truck_capacity_C']
    cost_A = params['warehouse_A_truck_cost']; cost_B = params['warehouse_B_truck_cost']
    fixed_A = params['warehouse_A_fixed_cost']; fixed_B = params['warehouse_B_fixed_cost']
    overflow_threshold = params['warehouse_B_overflow_threshold_trucks']
    overflow_cost = params['warehouse_B_overflow_coordination_cost']
    dual_fee = params['dual_warehouse_reconciliation_fee']

    prob = LpProblem('MinFreightFixedOverflowCost', LpMinimize)
    x = LpVariable('trucks_from_A', lowBound=0, cat='Integer')
    y = LpVariable('trucks_from_B', lowBound=0, cat='Integer')
    z_A = LpVariable('use_A', cat='Binary')
    z_B = LpVariable('use_B', cat='Binary')
    z_over = LpVariable('warehouse_B_overflow', cat='Binary')
    z_dual = LpVariable('dual_warehouse_reconciliation', cat='Binary')

    prob += cost_A * x + cost_B * y + fixed_A * z_A + fixed_B * z_B + overflow_cost * z_over + dual_fee * z_dual
    prob += cap_A_a * x + cap_B_a * y >= min_A
    prob += cap_A_b * x + cap_B_b * y >= min_B
    prob += cap_A_c * x + cap_B_c * y >= min_C
    M = 10000
    prob += x <= M * z_A
    prob += y <= M * z_B
    prob += y <= overflow_threshold + M * z_over
    prob += z_dual >= z_A + z_B - 1
    prob += z_dual <= z_A
    prob += z_dual <= z_B

    prob.solve(GUROBI_CMD(msg=0))
    print(f"OBJECTIVE_VALUE: {value(prob.objective)}")


if __name__ == '__main__':
    main()
