import os
import csv
from itertools import combinations
from utils import load_parameters

def solve():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    params = load_parameters(os.path.join(data_dir, 'general_parameters.csv'))

    profits = {
        'apples': params['profit_per_acre_apples'],
        'pears': params['profit_per_acre_pears'],
        'oranges': params['profit_per_acre_oranges'],
        'lemons': params['profit_per_acre_lemons'],
    }
    total_area = params['total_farm_area']
    min_a_to_p = params['min_apples_to_pears_ratio']
    min_a_to_l = params['min_apples_to_lemons_ratio']
    o_to_l = params['oranges_to_lemons_ratio']
    max_types = int(params['max_fruit_types'])

    fruits = ['apples', 'pears', 'oranges', 'lemons']
    
    best_obj = -1e30
    best_sol = None

    # Enumerate all subsets of size 1 to max_types
    for size in range(1, max_types + 1):
        for subset in combinations(fruits, size):
            subset_set = set(subset)
            
            # Use PuLP for each subproblem
            import gurobi_pulp_compat as pulp
            prob = pulp.LpProblem("farm", pulp.LpMaximize)
            x = {f: pulp.LpVariable(f"x_{f}", lowBound=0) for f in fruits}
            
            # Fix non-selected fruits to 0
            for f in fruits:
                if f not in subset_set:
                    prob += x[f] == 0
            
            prob += pulp.lpSum(profits[f] * x[f] for f in fruits)
            prob += pulp.lpSum(x[f] for f in fruits) <= total_area
            prob += x['apples'] >= min_a_to_p * x['pears']
            prob += x['apples'] >= min_a_to_l * x['lemons']
            prob += x['oranges'] == o_to_l * x['lemons']
            
            prob.solve(pulp.GUROBI_CMD(msg=0))
            
            if prob.status == 1:
                obj = pulp.value(prob.objective)
                if obj > best_obj:
                    best_obj = obj
                    best_sol = {f: pulp.value(x[f]) for f in fruits}

    print(f"Optimal solution: {best_sol}")
    print(f"OBJECTIVE_VALUE: {best_obj}")

solve()