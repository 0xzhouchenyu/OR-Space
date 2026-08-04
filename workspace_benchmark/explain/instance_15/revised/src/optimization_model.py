import os
import pandas as pd
import gurobi_pulp_compat as pulp

def load_data():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    table_1 = pd.read_csv(os.path.join(data_dir, 'table_1.csv'))
    params = pd.read_csv(os.path.join(data_dir, 'general_parameters.csv'))
    param_dict = dict(zip(params['Parameter_Name'], params['Value']))
    demand = dict(zip(table_1['stage'], table_1['tool_requirement']))
    return param_dict, demand

def solve():
    param_dict, demand = load_data()

    n = int(param_dict['n'])
    cost_new = float(param_dict['cost_new_tool'])
    cost_slow = float(param_dict['cost_slow_repair'])
    cost_fast = float(param_dict['cost_fast_repair'])
    dur_slow = int(param_dict['slow_repair_duration'])
    dur_fast = int(param_dict['fast_repair_duration'])

    max_fast_stage = float(param_dict['max_fast_stage'])
    max_slow_stage = float(param_dict['max_slow_stage'])
    emission_buy = float(param_dict['emission_buy'])
    emission_fast = float(param_dict['emission_fast_repair'])
    emission_slow = float(param_dict['emission_slow_repair'])
    carbon_budget = float(param_dict['carbon_budget'])
    penalty_shortage = float(param_dict['penalty_shortage'])

    prob = pulp.LpProblem("Tool_Repair_Carbon", pulp.LpMinimize)
    stages = list(range(1, n + 1))

    x = pulp.LpVariable.dicts("buy", stages, lowBound=0, cat='Integer')
    y = pulp.LpVariable.dicts("fast", stages, lowBound=0, cat='Integer')
    z = pulp.LpVariable.dicts("slow", stages, lowBound=0, cat='Integer')
    c = pulp.LpVariable.dicts("clean", [0] + stages, lowBound=0, cat='Integer')
    d = pulp.LpVariable.dicts("dirty", [0] + stages, lowBound=0, cat='Integer')
    u = pulp.LpVariable.dicts("used", stages, lowBound=0, cat='Integer')
    s = pulp.LpVariable.dicts("shortage", stages, lowBound=0, cat='Integer')
    prebuy0 = pulp.LpVariable("prebuy_clean0", lowBound=0, cat='Integer')

    prob += c[0] == prebuy0
    prob += d[0] == 0

    for i in stages:
        fast_ready = y[i - dur_fast - 1] if (i - dur_fast - 1) >= 1 else 0
        slow_ready = z[i - dur_slow - 1] if (i - dur_slow - 1) >= 1 else 0

        prob += c[i - 1] + x[i] + fast_ready + slow_ready == u[i] + c[i]
        prob += u[i] + d[i - 1] == y[i] + z[i] + d[i]
        prob += u[i] + s[i] == demand[i]
        prob += y[i] <= max_fast_stage
        prob += z[i] <= max_slow_stage

    emission_terms = [emission_buy * prebuy0]
    for i in stages:
        emission_terms.append(emission_buy * x[i])
        emission_terms.append(emission_fast * y[i])
        emission_terms.append(emission_slow * z[i])
    prob += pulp.lpSum(emission_terms) <= carbon_budget

    cost_terms = [cost_new * prebuy0]
    for i in stages:
        cost_terms.append(cost_new * x[i])
        cost_terms.append(cost_fast * y[i])
        cost_terms.append(cost_slow * z[i])
        cost_terms.append(penalty_shortage * s[i])
    prob += pulp.lpSum(cost_terms)

    prob.solve(pulp.GUROBI_CMD(msg=False))
    obj_val = pulp.value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    solve()
