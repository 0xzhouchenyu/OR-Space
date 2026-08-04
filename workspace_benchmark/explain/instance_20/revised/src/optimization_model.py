import os
import csv
from gurobi_pulp_compat import LpProblem, LpMaximize, LpVariable, LpStatus, GUROBI_CMD, value


def load_parameters():
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'general_parameters.csv')
    params = {}
    with open(filepath, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['Parameter_Name'].strip()
            raw_value = row['Value'].strip()
            try:
                val = int(raw_value)
            except ValueError:
                try:
                    val = float(raw_value)
                except ValueError:
                    val = raw_value
            params[name] = val
    return params


def solve():
    params = load_parameters()

    profit_robot = params['profit_per_robot']
    profit_car = params['profit_per_model_car']
    profit_blocks = params['profit_per_building_blocks']
    profit_doll = params['profit_per_doll']

    plastic_avail = params['plastic_available']
    electronics_avail = params['electronic_components_available']

    plastic_robot = params['plastic_per_robot']
    plastic_car = params['plastic_per_model_car']
    plastic_blocks = params['plastic_per_building_blocks']
    plastic_doll = params['plastic_per_doll']

    electronics_robot = params['electronics_per_robot']
    electronics_car = params['electronics_per_model_car']
    electronics_blocks = params['electronics_per_building_blocks']
    electronics_doll = params['electronics_per_doll']

    M = 10000

    prob = LpProblem('ToyManufacturing_Revised', LpMaximize)

    x_robot = LpVariable('robots', lowBound=0, cat='Integer')
    x_car = LpVariable('model_cars', lowBound=0, cat='Integer')
    x_blocks = LpVariable('building_blocks', lowBound=0, cat='Integer')
    x_doll = LpVariable('dolls', lowBound=0, cat='Integer')

    y_robot = LpVariable('y_robot', cat='Binary')
    y_doll = LpVariable('y_doll', cat='Binary')
    y_car = LpVariable('y_car', cat='Binary')
    y_blocks = LpVariable('y_blocks', cat='Binary')

    prob += profit_robot * x_robot + profit_car * x_car + profit_blocks * x_blocks + profit_doll * x_doll

    prob += plastic_robot * x_robot + plastic_car * x_car + plastic_blocks * x_blocks + plastic_doll * x_doll <= plastic_avail
    prob += electronics_robot * x_robot + electronics_car * x_car + electronics_blocks * x_blocks + electronics_doll * x_doll <= electronics_avail

    prob += x_robot <= M * y_robot
    prob += x_doll <= M * y_doll
    prob += x_car <= M * y_car
    prob += x_blocks <= M * y_blocks

    prob += y_robot <= x_robot
    prob += y_doll <= x_doll
    prob += y_car <= x_car
    prob += y_blocks <= x_blocks

    prob += y_robot + y_doll <= 1
    prob += y_car <= y_blocks
    prob += x_doll <= x_car

    # Revised mutual exclusion: model cars and building blocks cannot both be produced.
    prob += y_car + y_blocks <= 1

    prob.solve(GUROBI_CMD(msg=0))

    value_out = float(value(prob.objective))
    print(f'Status: {LpStatus[prob.status]}')
    print(f'Robots: {x_robot.varValue}')
    print(f'Model Cars: {x_car.varValue}')
    print(f'Building Blocks: {x_blocks.varValue}')
    print(f'Dolls: {x_doll.varValue}')
    print(f"OBJECTIVE_VALUE: {value_out}")


if __name__ == '__main__':
    solve()
