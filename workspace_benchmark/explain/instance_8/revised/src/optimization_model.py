import os
import csv
import gurobi_pulp_compat as pulp


def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    workers = []
    tasks = []
    cost = {}
    fixed_cost = {}
    with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        tasks = header[1:-1]
        for row in reader:
            worker = row[0].strip()
            workers.append(worker)
            for j, task in enumerate(tasks):
                cost[(worker, task)] = float(row[j + 1])
            fixed_cost[worker] = float(row[-1])

    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Parameter_Name'].strip():
                params[row['Parameter_Name'].strip()] = float(row['Value'])
    handoff_cost = params['shared_temp_handoff_cost']
    pair_ii_v_fee = params['worker_II_V_pair_fee']

    prob = pulp.LpProblem('Assignment_with_Temp_Handoff', pulp.LpMinimize)
    x = {(w, t): pulp.LpVariable(f'x_{w}_{t}', cat='Binary') for w in workers for t in tasks}
    y = {w: pulp.LpVariable(f'y_{w}', cat='Binary') for w in workers}
    h = pulp.LpVariable('shared_temp_handoff', cat='Binary')
    pair_ii_v = pulp.LpVariable('worker_II_V_pair', cat='Binary')

    prob += (
        pulp.lpSum(cost[w, t] * x[w, t] for w in workers for t in tasks)
        + pulp.lpSum(fixed_cost[w] * y[w] for w in workers)
        + handoff_cost * h
        + pair_ii_v_fee * pair_ii_v
    )
    for t in tasks:
        prob += pulp.lpSum(x[w, t] for w in workers) == 1
    for w in workers:
        prob += pulp.lpSum(x[w, t] for t in tasks) <= y[w]
    prob += h >= y['III'] + y['V'] - 1
    prob += h <= y['III']
    prob += h <= y['V']
    prob += pair_ii_v >= y['II'] + y['V'] - 1
    prob += pair_ii_v <= y['II']
    prob += pair_ii_v <= y['V']

    prob.solve(pulp.GUROBI_CMD(msg=0))
    print(f"OBJECTIVE_VALUE: {pulp.value(prob.objective)}")


if __name__ == '__main__':
    main()
