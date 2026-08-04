import os
from itertools import product
import gurobi_pulp_compat as pulp
from utils import load_parameters

def solve():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, '..', 'data')
    params = load_parameters(os.path.join(data_dir, 'general_parameters.csv'))

    fruits = ['apples', 'pears', 'oranges', 'lemons']
    seasons = ['spring', 'autumn']

    profit = {
        'apples': params['profit_per_acre_apples'],
        'pears': params['profit_per_acre_pears'],
        'oranges': params['profit_per_acre_oranges'],
        'lemons': params['profit_per_acre_lemons']
    }

    total_area = params['total_farm_area']
    min_a_to_p = params['min_apples_to_pears_ratio']
    min_a_to_l = params['min_apples_to_lemons_ratio']
    o_to_l = params['oranges_to_lemons_ratio']
    max_types = int(params['max_fruit_types'])

    water_per_acre = {}
    for f, s in product(fruits, seasons):
        key = f"water_per_acre_{f}_{s}"
        water_per_acre[(f, s)] = params[key]

    water_cap_spring = params['water_cap_spring']
    water_cap_autumn = params['water_cap_autumn']
    total_water_budget = params['total_water_budget']
    min_annual_water_per_fruit = params['min_annual_water_per_fruit']
    diversification_reward = params['diversification_reward']

    num_seasons = len(seasons)
    big_M_area = total_area * num_seasons

    max_water_per_acre = max(water_per_acre.values())
    big_M_water = max_water_per_acre * big_M_area

    prob = pulp.LpProblem('farm_two_seasons_water', pulp.LpMaximize)

    area = {(f, s): pulp.LpVariable(f"area_{f}_{s}", lowBound=0) for f, s in product(fruits, seasons)}
    water = {(f, s): pulp.LpVariable(f"water_{f}_{s}", lowBound=0) for f, s in product(fruits, seasons)}

    y = {f: pulp.LpVariable(f"y_{f}", lowBound=0, upBound=1, cat='Binary') for f in fruits}
    z = {f: pulp.LpVariable(f"z_{f}", lowBound=0, upBound=1, cat='Binary') for f in fruits}
    v = pulp.LpVariable("v", lowBound=0, upBound=1, cat='Binary')

    profit_term = []
    for f, s in product(fruits, seasons):
        profit_term.append(profit[f] * area[(f, s)])
    prob += pulp.lpSum(profit_term) + diversification_reward * v

    for s in seasons:
        prob += pulp.lpSum(area[(f, s)] for f in fruits) <= total_area, f"land_season_{s}"

    area_total = {f: pulp.lpSum(area[(f, s)] for s in seasons) for f in fruits}

    prob += area_total['apples'] >= min_a_to_p * area_total['pears'], "ratio_apples_pears"
    prob += area_total['apples'] >= min_a_to_l * area_total['lemons'], "ratio_apples_lemons"
    prob += area_total['oranges'] == o_to_l * area_total['lemons'], "ratio_oranges_lemons"

    for f in fruits:
        prob += area_total[f] <= big_M_area * y[f], f"link_area_y_{f}"
    prob += pulp.lpSum(y[f] for f in fruits) <= max_types, "max_types_rule"

    for f, s in product(fruits, seasons):
        prob += water[(f, s)] == water_per_acre[(f, s)] * area[(f, s)], f"water_def_{f}_{s}"

    prob += pulp.lpSum(water[(f, 'spring')] for f in fruits) <= water_cap_spring, "water_cap_spring"
    prob += pulp.lpSum(water[(f, 'autumn')] for f in fruits) <= water_cap_autumn, "water_cap_autumn"

    prob += pulp.lpSum(water[(f, s)] for f, s in product(fruits, seasons)) <= total_water_budget, "total_water_budget"

    water_total = {f: pulp.lpSum(water[(f, s)] for s in seasons) for f in fruits}
    for f in fruits:
        prob += water_total[f] <= big_M_water * z[f], f"link_water_z_ub_{f}"
        prob += water_total[f] >= min_annual_water_per_fruit * z[f], f"link_water_z_lb_{f}"
        # Consistency: z_f == y_f
        prob += z[f] == y[f], f"z_eq_y_{f}"

    # Diversification: v=1 iff at least two fruits activated
    N = pulp.lpSum(y[f] for f in fruits)
    prob += 2 * v <= N, "div_min_two"
    prob += N <= 1 + 4 * v, "div_upper"

    prob.solve(pulp.GUROBI_CMD(msg=0))

    if prob.status != 1:
        raise RuntimeError("Optimization did not find an optimal solution")

    obj_value = pulp.value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj_value}")

if __name__ == "__main__":
    solve()
