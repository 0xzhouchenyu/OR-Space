import pandas as pd
import gurobi_pulp_compat as pulp
from utils import get_data_path

def solve():
    # Load data
    demand_df = pd.read_csv(get_data_path('table_4_3.csv'))
    supply_df = pd.read_csv(get_data_path('table_4_4.csv'))
    params_df = pd.read_csv(get_data_path('general_parameters.csv'))
    
    # Parse parameters
    p2_target = float(params_df[params_df['Parameter_Name'] == 'priority_2_target']['Value'].iloc[0])
    p3_target = float(params_df[params_df['Parameter_Name'] == 'priority_3_target']['Value'].iloc[0])
    
    # Parse demand
    demand = {}
    for _, row in demand_df.iterrows():
        city = row['Branch_Location'].split(' ')[0]
        spec = int(row['Specialty'])
        dem = float(row['Demand'])
        demand[(city, spec)] = dem
        
    # Parse supply
    supply = {}
    for _, row in supply_df.iterrows():
        t = int(row['Type'])
        num = float(row['Number_of_People'])
        suit = [int(x) for x in str(row['Suitable_Specialty']).split(',')]
        pref_spec = int(row['Preferred_Specialty'])
        pref_city = row['Preferred_City']
        supply[t] = {
            'num': num,
            'suit': suit,
            'pref_spec': pref_spec,
            'pref_city': pref_city
        }
        
    cities = ['Donghai', 'Nanjiang']
    specs = [1, 2, 3]
    types = [1, 2, 3, 4, 5, 6]
    
    # Problem 1: Minimize d2_minus (Priority 2)
    prob1 = pulp.LpProblem("P1", pulp.LpMinimize)
    
    x1 = pulp.LpVariable.dicts("x1", ((i, j, k) for i in types for j in cities for k in specs), lowBound=0, cat='Integer')
    d2_minus1 = pulp.LpVariable("d2_minus1", lowBound=0, cat='Integer')
    d2_plus1 = pulp.LpVariable("d2_plus1", lowBound=0, cat='Integer')
    
    # Constraints
    for i in types:
        prob1 += pulp.lpSum(x1[i, j, k] for j in cities for k in specs) <= supply[i]['num']
        
    for j in cities:
        for k in specs:
            prob1 += pulp.lpSum(x1[i, j, k] for i in types) >= demand[(j, k)]
            
    for i in types:
        for j in cities:
            for k in specs:
                if k not in supply[i]['suit']:
                    prob1 += x1[i, j, k] == 0
                    
    p2_expr1 = pulp.lpSum(x1[i, j, supply[i]['pref_spec']] for i in types for j in cities)
    prob1 += p2_expr1 + d2_minus1 - d2_plus1 == p2_target
    
    prob1 += d2_minus1
    prob1.solve(pulp.GUROBI_CMD(msg=False))
    
    min_d2 = round(pulp.value(d2_minus1))
    
    # Problem 2: Minimize d3_minus (Priority 3)
    prob2 = pulp.LpProblem("P2", pulp.LpMinimize)
    
    x2 = pulp.LpVariable.dicts("x2", ((i, j, k) for i in types for j in cities for k in specs), lowBound=0, cat='Integer')
    d2_minus2 = pulp.LpVariable("d2_minus2", lowBound=0, cat='Integer')
    d2_plus2 = pulp.LpVariable("d2_plus2", lowBound=0, cat='Integer')
    d3_minus2 = pulp.LpVariable("d3_minus2", lowBound=0, cat='Integer')
    d3_plus2 = pulp.LpVariable("d3_plus2", lowBound=0, cat='Integer')
    
    # Constraints
    for i in types:
        prob2 += pulp.lpSum(x2[i, j, k] for j in cities for k in specs) <= supply[i]['num']
        
    for j in cities:
        for k in specs:
            prob2 += pulp.lpSum(x2[i, j, k] for i in types) >= demand[(j, k)]
            
    for i in types:
        for j in cities:
            for k in specs:
                if k not in supply[i]['suit']:
                    prob2 += x2[i, j, k] == 0
                    
    p2_expr2 = pulp.lpSum(x2[i, j, supply[i]['pref_spec']] for i in types for j in cities)
    prob2 += p2_expr2 + d2_minus2 - d2_plus2 == p2_target
    prob2 += d2_minus2 <= min_d2
    
    p3_expr2 = pulp.lpSum(x2[i, supply[i]['pref_city'], k] for i in types for k in specs)
    prob2 += p3_expr2 + d3_minus2 - d3_plus2 == p3_target
    
    prob2 += d3_minus2
    prob2.solve(pulp.GUROBI_CMD(msg=False))
    
    min_d3 = pulp.value(d3_minus2)
    print(f"OBJECTIVE_VALUE: {min_d3}")

if __name__ == '__main__':
    solve()