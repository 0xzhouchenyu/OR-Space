import os
import csv
from gurobi_pulp_compat import *


def read_table_1(data_dir):
    workshops = []
    capacities = {}
    rates = {}
    filepath = os.path.join(data_dir, 'table_1.csv')
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            w = row['Workshop'].strip()
            workshops.append(w)
            capacities[w] = float(row['Production_Capacity_hours'].strip())
            rates[(w, 1)] = float(row['Production_Rate_Component_1_units_per_hour'].strip())
            rates[(w, 2)] = float(row['Production_Rate_Component_2_units_per_hour'].strip())
            rates[(w, 3)] = float(row['Production_Rate_Component_3_units_per_hour'].strip())
    return workshops, capacities, rates


def read_general_parameters(data_dir):
    params = {}
    filepath = os.path.join(data_dir, 'general_parameters.csv')
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['Parameter_Name'].strip()
            if not name:
                continue
            value = float(row['Value'].strip())
            params[name] = value
    return params


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, '..', 'data')

    workshops, capacities, rates = read_table_1(data_dir)
    params = read_general_parameters(data_dir)

    components = [1, 2, 3]
    shifts = ['day', 'night']

    # Helper functions for parameter names
    def reg_limit_name(w, s):
        return f"regular_hours_limit_{s}_{w}"

    def ot_cap_name(w, s):
        return f"overtime_capacity_{s}_{w}"

    def bigM_name(w):
        return f"bigM_shift_{w}"

    # Global parameters
    penalty_night_hour = params['penalty_night_hour']
    penalty_overtime_hour = params['penalty_overtime_hour']
    penalty_shortage_per_unit = params['penalty_shortage_per_unit']
    z_target = params['z_target']

    # Create MILP problem: minimize total penalty cost
    prob = LpProblem("Shift_Based_Production_Planning", LpMinimize)

    # Decision variables
    x_reg = {}  # regular-time hours
    x_ot = {}   # overtime hours
    for w in workshops:
        for c in components:
            for s in shifts:
                x_reg[(w, c, s)] = LpVariable(f"x_reg_{w}_{c}_{s}", lowBound=0)
                x_ot[(w, c, s)] = LpVariable(f"x_ot_{w}_{c}_{s}", lowBound=0)

    # Active indicator per workshop and shift
    y = {}
    for w in workshops:
        for s in shifts:
            y[(w, s)] = LpVariable(f"y_{w}_{s}", lowBound=0, upBound=1, cat=LpBinary)

    # Completed products and shortfall
    z = LpVariable("z", lowBound=0)
    shortfall = LpVariable("shortfall", lowBound=0)

    # 1. Regular-time limits per workshop and shift
    for w in workshops:
        for s in shifts:
            reg_limit = params[reg_limit_name(w, s)]
            prob += (
                lpSum(x_reg[(w, c, s)] for c in components) <= reg_limit,
                f"RegLimit_{w}_{s}"
            )

    # 2. Overtime capacity per workshop and shift
    for w in workshops:
        for s in shifts:
            ot_cap = params[ot_cap_name(w, s)]
            prob += (
                lpSum(x_ot[(w, c, s)] for c in components) <= ot_cap,
                f"OTCap_{w}_{s}"
            )

    # 3. Total hours vs original capacity per workshop
    for w in workshops:
        prob += (
            lpSum(x_reg[(w, c, s)] + x_ot[(w, c, s)] for c in components for s in shifts) <= capacities[w],
            f"TotalCap_{w}"
        )

    # 4. Link y[w,s] to hours via big-M
    for w in workshops:
        bigM = params[bigM_name(w)]
        for s in shifts:
            prob += (
                lpSum(x_reg[(w, c, s)] + x_ot[(w, c, s)] for c in components) <= bigM * y[(w, s)],
                f"LinkY_{w}_{s}"
            )

    # 5. At most two active workshops per shift
    for s in shifts:
        prob += (
            lpSum(y[(w, s)] for w in workshops) <= 2,
            f"MaxActive_{s}"
        )

    # 6. Definition of completed products z <= total production for each component
    for c in components:
        total_prod_c = lpSum(rates[(w, c)] * (x_reg[(w, c, s)] + x_ot[(w, c, s)])
                             for w in workshops for s in shifts)
        prob += (
            z <= total_prod_c,
            f"Min_component_{c}"
        )

    # 7. Shortfall definition: shortfall >= z_target - z and >=0 implicit from variable bounds
    prob += (
        shortfall >= z_target - z,
        "Shortfall_def"
    )

    # Objective: minimize penalties for night regular hours, overtime hours, and product shortfall
    night_reg_hours = lpSum(x_reg[(w, c, 'night')] for w in workshops for c in components)
    overtime_hours = lpSum(x_ot[(w, c, s)] for w in workshops for c in components for s in shifts)

    total_cost = (
        penalty_night_hour * night_reg_hours
        + penalty_overtime_hour * overtime_hours
        + penalty_shortage_per_unit * shortfall
    )

    prob += total_cost, "Minimize_total_penalty_cost"

    # Solve the problem
    prob.solve(GUROBI_CMD(msg=0))

    obj_val = value(prob.objective)
    # Print only OBJECTIVE_VALUE line as required
    print(f"OBJECTIVE_VALUE: {obj_val:.4f}")


if __name__ == "__main__":
    main()
