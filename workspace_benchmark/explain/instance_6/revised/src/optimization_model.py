import os
import csv
from gurobi_pulp_compat import LpProblem, LpMinimize, LpVariable, lpSum, GUROBI_CMD, value


def load_data(base_dir):
    demand = {}
    with open(os.path.join(base_dir, 'table_1.csv'), 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        quarters = [int(h) for h in header[1:]]
        for row in reader:
            product = row[0].strip()
            for j, q in enumerate(quarters):
                demand[(product, q)] = int(row[j + 1])

    params = {}
    with open(os.path.join(base_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name'].strip()] = float(row['Value'])

    return demand, params


def main():
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

    demand, params = load_data(base_dir)

    products = ['I', 'II', 'III']
    quarters = [1, 2, 3, 4]

    init_inv = params['initial_inventory']
    end_inv_req = params['end_inventory_requirement']
    hours_per_quarter = params['production_hours_per_quarter']

    hours_per_unit = {
        'I': params['product_I_hours_per_unit'],
        'II': params['product_II_hours_per_unit'],
        'III': params['product_III_hours_per_unit']
    }

    delay_penalty = {
        'I': params['delay_penalty_product_I'],
        'II': params['delay_penalty_product_II'],
        'III': params['delay_penalty_product_III']
    }

    inv_cost = params['inventory_cost_per_unit']

    normal_frac = {
        1: params['normal_hours_cap_fraction_q1'],
        2: params['normal_hours_cap_fraction_q2'],
        3: params['normal_hours_cap_fraction_q3'],
        4: params['normal_hours_cap_fraction_q4']
    }

    peak_cap = {
        1: params['peak_hours_cap_q1'],
        2: params['peak_hours_cap_q2'],
        3: params['peak_hours_cap_q3'],
        4: params['peak_hours_cap_q4']
    }

    peak_cost = {
        1: params['peak_cost_per_hour_q1'],
        2: params['peak_cost_per_hour_q2'],
        3: params['peak_cost_per_hour_q3'],
        4: params['peak_cost_per_hour_q4']
    }

    prob = LpProblem("ProductionScheduling_PeakSplit", LpMinimize)

    # Decision variables: normal and peak production quantities
    x = {(p, t): LpVariable(f"x_{p}_{t}", lowBound=0, cat='Continuous') for p in products for t in quarters}
    x_peak = {(p, t): LpVariable(f"x_peak_{p}_{t}", lowBound=0, cat='Continuous') for p in products for t in quarters}

    # Total production q = x + x_peak
    q = {(p, t): LpVariable(f"q_{p}_{t}", lowBound=0, cat='Continuous') for p in products for t in quarters}

    # Product I cannot be produced in Q2 (neither normal nor peak)
    x[('I', 2)].upBound = 0
    x_peak[('I', 2)].upBound = 0

    # Inventory variables
    inv = {(p, t): LpVariable(f"inv_{p}_{t}") for p in products for t in quarters}
    inv_pos = {(p, t): LpVariable(f"inv_pos_{p}_{t}", lowBound=0) for p in products for t in quarters}
    inv_neg = {(p, t): LpVariable(f"inv_neg_{p}_{t}", lowBound=0) for p in products for t in quarters}

    # Link total production q with normal and peak production
    for p in products:
        for t in quarters:
            prob += q[(p, t)] == x[(p, t)] + x_peak[(p, t)]

    # Inventory balance constraints
    for p in products:
        # Quarter 1
        prob += inv[(p, 1)] == init_inv + q[(p, 1)] - demand[(p, 1)]
        # Quarters 2-4
        for t in range(2, 5):
            prob += inv[(p, t)] == inv[(p, t - 1)] + q[(p, t)] - demand[(p, t)]

    # Split inventory into positive and negative parts
    for p in products:
        for t in quarters:
            prob += inv[(p, t)] == inv_pos[(p, t)] - inv_neg[(p, t)]

    # End of Q4: inventory must be at least end_inv_req
    for p in products:
        prob += inv[(p, 4)] >= end_inv_req

    # Normal-hours capacity constraint per quarter
    for t in quarters:
        prob += (
            lpSum(hours_per_unit[p] * x[(p, t)] for p in products)
            <= normal_frac[t] * hours_per_quarter
        )

    # Peak-hours capacity constraint per quarter
    for t in quarters:
        prob += (
            lpSum(hours_per_unit[p] * x_peak[(p, t)] for p in products)
            <= peak_cap[t]
        )

    # Objective: delay penalties + inventory holding costs + peak-hour energy costs
    delay_cost = lpSum(
        delay_penalty[p] * inv_neg[(p, t)]
        for p in products for t in quarters
    )

    inventory_cost = lpSum(
        inv_cost * inv_pos[(p, t)]
        for p in products for t in quarters
    )

    peak_energy_cost = lpSum(
        peak_cost[t] * lpSum(hours_per_unit[p] * x_peak[(p, t)] for p in products)
        for t in quarters
    )

    prob += delay_cost + inventory_cost + peak_energy_cost

    prob.solve(GUROBI_CMD(msg=0, timeLimit=30))

    obj_val = value(prob.objective)
    if obj_val is None:
        print("OBJECTIVE_VALUE: nan")
    else:
        print(f"OBJECTIVE_VALUE: {obj_val}")


if __name__ == "__main__":
    main()
