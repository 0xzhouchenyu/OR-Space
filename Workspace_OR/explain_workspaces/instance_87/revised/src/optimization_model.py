import os
import csv
import gurobi_pulp_compat as pulp


def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            params[row['Parameter_Name']] = float(row['Value'])

    x = pulp.LpVariable('TypeA_trucks', lowBound=0, cat='Integer')
    y = pulp.LpVariable('TypeB_trucks', lowBound=0, cat='Integer')
    x_extra = pulp.LpVariable('TypeA_extra', lowBound=0, cat='Integer')
    y_extra = pulp.LpVariable('TypeB_extra', lowBound=0, cat='Integer')
    y_over = pulp.LpVariable('TypeB_recovery_desk', cat='Binary')
    fleet_surge = pulp.LpVariable('total_fleet_surge', cat='Binary')
    prob = pulp.LpProblem('TruckRental_TypeBRecovery', pulp.LpMinimize)

    prob += (
        params['rental_cost_type_a'] * x
        + params['rental_cost_type_b'] * y
        + params['penalty_cost_type_a'] * x_extra
        + params['penalty_cost_type_b'] * y_extra
        + params['type_b_recovery_fee'] * y_over
        + params['total_fleet_surge_fee'] * fleet_surge
    )
    prob += params['refrigerated_capacity_type_a'] * x + params['refrigerated_capacity_type_b'] * y >= params['refrigerated_cargo_requirement']
    prob += params['non_refrigerated_capacity_type_a'] * x + params['non_refrigerated_capacity_type_b'] * y >= params['non_refrigerated_cargo_requirement']
    prob += x_extra >= x - params['base_fleet_type_a']
    prob += y_extra >= y - params['base_fleet_type_b']
    prob += y <= params['type_b_recovery_threshold'] + 10000 * y_over
    prob += x + y <= params['total_fleet_surge_threshold'] + 10000 * fleet_surge

    prob.solve(pulp.GUROBI_CMD(msg=0))
    print(f"OBJECTIVE_VALUE: {pulp.value(prob.objective)}")


if __name__ == '__main__':
    main()
