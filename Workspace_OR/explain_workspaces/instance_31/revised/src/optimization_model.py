import os
import csv
from gurobi_pulp_compat import LpProblem, LpMaximize, LpVariable, lpSum, LpBinary, GUROBI_CMD, LpStatus, value


def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

    proc_time = {}
    capacity = {}
    cost_rate = {}
    raw_cost = {}
    price = {}

    with open(os.path.join(data_dir, 'table_1.csv'), 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            equip = row['Equipment'].strip()
            if equip == 'Raw_Material_Cost':
                raw_cost = {
                    'I': float(row['Product_I']),
                    'II': float(row['Product_II']),
                    'III': float(row['Product_III'])
                }
            elif equip == 'Unit_Price':
                price = {
                    'I': float(row['Product_I']),
                    'II': float(row['Product_II']),
                    'III': float(row['Product_III'])
                }
            else:
                for prod, col in [('I', 'Product_I'), ('II', 'Product_II'), ('III', 'Product_III')]:
                    val = row[col].strip()
                    if val != '-':
                        proc_time[(equip, prod)] = float(val)
                capacity[equip] = float(row['Effective_Machine_Hours'])
                cost_rate[equip] = float(row['Processing_Cost_per_Machine_Hour'])

    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw = row['Value'].strip()
            try:
                params[row['Parameter_Name'].strip()] = float(raw)
            except ValueError:
                params[row['Parameter_Name'].strip()] = raw

    setup_cost = {}
    with open(os.path.join(data_dir, 'setup_costs.csv'), 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            setup_cost[row['Equipment'].strip()] = float(row['Fixed_Setup_Cost'])

    stage_A_equip = {'I': ['A1', 'A2'], 'II': ['A1', 'A2'], 'III': ['A2']}
    stage_B_equip = {'I': ['B1', 'B2', 'B3'], 'II': ['B1'], 'III': ['B2']}
    all_equipment = ['A1', 'A2', 'B1', 'B2', 'B3']
    products = ['I', 'II', 'III']

    prob = LpProblem('Factory_Production_With_Setup_Costs', LpMaximize)

    x = {}
    for prod in products:
        for equip in stage_A_equip[prod]:
            x[(equip, prod)] = LpVariable(f'x_{equip}_{prod}', lowBound=0)
        for equip in stage_B_equip[prod]:
            if (equip, prod) not in x:
                x[(equip, prod)] = LpVariable(f'x_{equip}_{prod}', lowBound=0)

    y = {e: LpVariable(f'y_{e}', cat=LpBinary) for e in all_equipment}
    joint_calibration = LpVariable('A2_B2_joint_calibration', cat=LpBinary)

    total = {}
    for prod in products:
        total[prod] = lpSum(x[(e, prod)] for e in stage_A_equip[prod])
        prob += lpSum(x[(e, prod)] for e in stage_A_equip[prod]) == lpSum(x[(e, prod)] for e in stage_B_equip[prod]), f'flow_balance_{prod}'

    for equip in all_equipment:
        relevant = [(equip, prod) for prod in products if (equip, prod) in x]
        if relevant:
            used_hours = lpSum(proc_time[(equip, prod)] * x[(equip, prod)] for (_, prod) in relevant)
            prob += used_hours <= capacity[equip], f'capacity_{equip}'
            prob += used_hours <= capacity[equip] * y[equip], f'activation_{equip}'
        else:
            prob += y[equip] == 0, f'no_use_{equip}'

    prob += joint_calibration >= y['A2'] + y['B2'] - 1, 'A2_B2_joint_calibration_lower'
    prob += joint_calibration <= y['A2'], 'A2_B2_joint_calibration_A2'
    prob += joint_calibration <= y['B2'], 'A2_B2_joint_calibration_B2'

    revenue = lpSum(price[p] * total[p] for p in products)
    raw_mat = lpSum(raw_cost[p] * total[p] for p in products)
    proc_cost = lpSum(cost_rate[e] * proc_time[(e, p)] * x[(e, p)] for (e, p) in x)
    fixed_setup = lpSum(setup_cost[e] * y[e] for e in all_equipment)
    joint_calibration_cost = params['A2_B2_joint_calibration_fee'] * joint_calibration

    prob += revenue - raw_mat - proc_cost - fixed_setup - joint_calibration_cost

    prob.solve(GUROBI_CMD(msg=0))

    print(f'Status: {LpStatus[prob.status]}')
    for v in prob.variables():
        if v.varValue is not None and v.varValue > 1e-8:
            print(f'{v.name} = {v.varValue}')

    value_out = round(value(prob.objective), 2)
    print(f"OBJECTIVE_VALUE: {value_out}")


if __name__ == '__main__':
    main()
