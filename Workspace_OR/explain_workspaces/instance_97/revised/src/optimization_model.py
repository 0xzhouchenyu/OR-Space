import os
import csv
from gurobi_pulp_compat import *

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, '..', 'data')

    # Read table_1.csv
    materials = []
    sulfur_content = {}
    purchase_price = {}

    with open(os.path.join(data_dir, 'table_1.csv'), 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            mat = row['Material'].strip()
            materials.append(mat)
            if ' Sulfur_Content_Percentage' in row:
                sulfur_content[mat] = float(row[' Sulfur_Content_Percentage'].strip())
            else:
                sulfur_content[mat] = float(row['Sulfur_Content_Percentage'].strip())
            for key in row:
                if 'Purchase_Price' in key:
                    purchase_price[mat] = float(row[key].strip())

    # Read general_parameters.csv
    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            param_name = row['Parameter_Name'].strip()
            if ' Value' in row:
                val = float(row[' Value'].strip())
            else:
                val = float(row['Value'].strip())
            params[param_name] = val

    # Sulfur limits per product and tier
    max_sulfur_A_prem = params['max_sulfur_content_A_premium']
    max_sulfur_A_std = params['max_sulfur_content_A_standard']
    max_sulfur_B_prem = params['max_sulfur_content_B_premium']
    max_sulfur_B_std = params['max_sulfur_content_B_standard']

    # Selling prices per product and tier
    price_A_prem = params['selling_price_A_premium']
    price_A_std = params['selling_price_A_standard']
    price_B_prem = params['selling_price_B_premium']
    price_B_std = params['selling_price_B_standard']

    # Supply and demand limits
    max_supply_D = params['max_supply_D']
    demand_A = params['market_demand_A']
    demand_B = params['market_demand_B']

    # Premium share bounds
    min_prem_A = params['min_premium_share_A']
    max_prem_A = params['max_premium_share_A']
    min_prem_B = params['min_premium_share_B']
    max_prem_B = params['max_premium_share_B']

    # Products with tiers
    products = ['ProdA_premium', 'ProdA_standard', 'ProdB_premium', 'ProdB_standard']

    # Decision variables
    prob = LpProblem('Mixing_Problem_Tiered', LpMaximize)
    x = {}
    for m in materials:
        for p in products:
            x[m, p] = LpVariable(f'x_{m}_{p}', lowBound=0)

    # Total quantities
    total_A_prem = lpSum([x[m, 'ProdA_premium'] for m in materials])
    total_A_std = lpSum([x[m, 'ProdA_standard'] for m in materials])
    total_B_prem = lpSum([x[m, 'ProdB_premium'] for m in materials])
    total_B_std = lpSum([x[m, 'ProdB_standard'] for m in materials])

    # Revenue
    revenue = (
        price_A_prem * total_A_prem +
        price_A_std * total_A_std +
        price_B_prem * total_B_prem +
        price_B_std * total_B_std
    )

    # Cost
    cost = lpSum([
        purchase_price[m] * (
            x[m, 'ProdA_premium'] + x[m, 'ProdA_standard'] +
            x[m, 'ProdB_premium'] + x[m, 'ProdB_standard']
        ) for m in materials
    ])

    # Objective
    prob += revenue - cost, 'Profit_Tiered'

    # Sulfur constraints
    prob += lpSum([sulfur_content[m] * x[m, 'ProdA_premium'] for m in materials]) <= max_sulfur_A_prem * total_A_prem, 'Sulfur_A_premium'
    prob += lpSum([sulfur_content[m] * x[m, 'ProdA_standard'] for m in materials]) <= max_sulfur_A_std * total_A_std, 'Sulfur_A_standard'
    prob += lpSum([sulfur_content[m] * x[m, 'ProdB_premium'] for m in materials]) <= max_sulfur_B_prem * total_B_prem, 'Sulfur_B_premium'
    prob += lpSum([sulfur_content[m] * x[m, 'ProdB_standard'] for m in materials]) <= max_sulfur_B_std * total_B_std, 'Sulfur_B_standard'

    # Supply constraint for D
    prob += (
        x['D', 'ProdA_premium'] + x['D', 'ProdA_standard'] +
        x['D', 'ProdB_premium'] + x['D', 'ProdB_standard']
    ) <= max_supply_D, 'Supply_D_total'

    # Demand constraints
    prob += total_A_prem + total_A_std <= demand_A, 'Demand_A_family'
    prob += total_B_prem + total_B_std <= demand_B, 'Demand_B_family'

    # Premium share bounds
    prob += total_A_prem >= min_prem_A, 'Min_Premium_A'
    prob += total_A_prem <= max_prem_A, 'Max_Premium_A'
    prob += total_B_prem >= min_prem_B, 'Min_Premium_B'
    prob += total_B_prem <= max_prem_B, 'Max_Premium_B'

    # Solve
    prob.solve(GUROBI_CMD(msg=0))

    # Print solution
    print('Status:', LpStatus[prob.status])
    for m in materials:
        for p in products:
            v = x[m, p].varValue
            if v is not None and v > 1e-6:
                print(f'  x[{m},{p}] = {v:.4f}')

    obj_val = value(prob.objective)
    print('OBJECTIVE_VALUE:', obj_val)

if __name__ == '__main__':
    main()
