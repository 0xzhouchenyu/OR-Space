import os
import pandas as pd
import gurobi_pulp_compat as pulp


def solve():
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    demand_df = pd.read_csv(os.path.join(base_dir, 'table_4_3.csv'))
    supply_df = pd.read_csv(os.path.join(base_dir, 'table_4_4.csv'))
    params_df = pd.read_csv(os.path.join(base_dir, 'general_parameters.csv'))

    p2_target = float(params_df.loc[params_df['Parameter_Name'] == 'priority_2_target', 'Value'].iloc[0])

    demand = {}
    for _, row in demand_df.iterrows():
        city = row['Branch_Location'].split(' ')[0]
        spec = int(row['Specialty'])
        demand[(city, spec)] = float(row['Demand'])

    supply = {}
    for _, row in supply_df.iterrows():
        t = int(row['Type'])
        suit = [int(x) for x in str(row['Suitable_Specialty']).split(',')]
        supply[t] = {
            'num': float(row['Number_of_People']),
            'suit': suit,
            'pref_spec': int(row['Preferred_Specialty']),
            'pref_city': str(row['Preferred_City']).strip()
        }

    cities = ['Donghai', 'Nanjiang']
    specs = [1, 2, 3]
    types = sorted(supply.keys())

    prob = pulp.LpProblem('Revised_HR_Placement', pulp.LpMaximize)

    x = pulp.LpVariable.dicts(
        'x',
        ((i, j, k) for i in types for j in cities for k in specs),
        lowBound=0,
        cat='Integer'
    )

    for i in types:
        prob += pulp.lpSum(x[i, j, k] for j in cities for k in specs) <= supply[i]['num']

    for j in cities:
        for k in specs:
            prob += pulp.lpSum(x[i, j, k] for i in types) >= demand[(j, k)]

    for i in types:
        for j in cities:
            for k in specs:
                if k not in supply[i]['suit']:
                    prob += x[i, j, k] == 0

    preferred_specialty_count = pulp.lpSum(
        x[i, j, supply[i]['pref_spec']]
        for i in types for j in cities
        if supply[i]['pref_spec'] in supply[i]['suit']
    )
    prob += preferred_specialty_count >= p2_target

    dual_match_count = pulp.lpSum(
        x[i, supply[i]['pref_city'], supply[i]['pref_spec']]
        for i in types
        if supply[i]['pref_spec'] in supply[i]['suit']
    )

    prob += dual_match_count

    prob.solve(pulp.GUROBI_CMD(msg=False))

    value = float(pulp.value(dual_match_count))
    print(f"OBJECTIVE_VALUE: {value}")


if __name__ == '__main__':
    solve()
