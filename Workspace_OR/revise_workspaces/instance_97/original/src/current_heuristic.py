import gurobi_pulp_compat as pulp
import os
import csv
from gurobi_pulp_compat import *

def main():
    # Get data directory
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
            sulfur_content[mat] = float(row[' Sulfur_Content_Percentage'].strip()) if ' Sulfur_Content_Percentage' in row else float(row['Sulfur_Content_Percentage'].strip())
            # Handle possible space in column names
            for key in row:
                if 'Purchase_Price' in key:
                    purchase_price[mat] = float(row[key].strip())
    
    # Read general_parameters.csv
    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            param_name = row['Parameter_Name'].strip()
            val = float(row[' Value'].strip()) if ' Value' in row else float(row['Value'].strip())
            params[param_name] = val
    
    max_sulfur_A = params['max_sulfur_content_A']  # 2.5%
    max_sulfur_B = params['max_sulfur_content_B']  # 1.5%
    selling_price = params['selling_price_A_B']     # 9.15 thousand yuan per ton
    max_supply_D = params['max_supply_D']           # 50 tons
    demand_A = params['market_demand_A']            # 100 tons
    demand_B = params['market_demand_B']            # 200 tons
    
    products = ['ProdA', 'ProdB']
    
    # Decision variables: x[m, p] = tons of material m used in product p
    prob = LpProblem("Mixing_Problem", LpMaximize)
    
    x = {}
    for m in materials:
        for p in products:
            x[m, p] = LpVariable(f"x_{m}_{p}", lowBound=0)
    
    # Total amount of each product
    # total_A = sum of x[m, 'ProdA'] for all m
    # total_B = sum of x[m, 'ProdB'] for all m
    
    total_A = lpSum([x[m, 'ProdA'] for m in materials])
    total_B = lpSum([x[m, 'ProdB'] for m in materials])
    
    # Revenue - Cost
    revenue = selling_price * (total_A + total_B)
    cost = lpSum([purchase_price[m] * (x[m, 'ProdA'] + x[m, 'ProdB']) for m in materials])
    
    prob += revenue - cost, "Profit"
    
    # Sulfur content constraints for product A: sum(sulfur[m]*x[m,A]) <= max_sulfur_A * sum(x[m,A])
    prob += lpSum([sulfur_content[m] * x[m, 'ProdA'] for m in materials]) <= max_sulfur_A * total_A, "Sulfur_A"
    
    # Sulfur content constraints for product B: sum(sulfur[m]*x[m,B]) <= max_sulfur_B * sum(x[m,B])
    prob += lpSum([sulfur_content[m] * x[m, 'ProdB'] for m in materials]) <= max_sulfur_B * total_B, "Sulfur_B"
    
    # Supply limit for material D
    prob += x['D', 'ProdA'] + x['D', 'ProdB'] <= max_supply_D, "Supply_D"
    
    # Market demand constraints
    prob += total_A <= demand_A, "Demand_A"
    prob += total_B <= demand_B, "Demand_B"
    
    # Solve
    prob.solve(GUROBI_CMD(msg=0))
    
    # Print solution details
    print(f"Status: {LpStatus[prob.status]}")
    
    for m in materials:
        for p in products:
            v = x[m, p].varValue
            if v is not None and v > 1e-6:
                print(f"  x[{m},{p}] = {v:.4f}")
    
    obj_val = pulp.value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()