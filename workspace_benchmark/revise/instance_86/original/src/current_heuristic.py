import os
import csv
from utils import load_csv_data

def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    
    # Load data
    products = load_csv_data(os.path.join(data_dir, 'table_1.csv'))
    params_raw = load_csv_data(os.path.join(data_dir, 'general_parameters.csv'))
    
    # Parse general parameters
    params = {}
    for row in params_raw:
        params[row['Parameter_Name']] = float(row['Value'])
    
    max_grains = params['max_grains']
    price_grains = params['price_per_lb_grains']
    max_meat = params['max_meat']
    price_meat = params['price_per_lb_meat']
    
    # Parse product data
    product_data = {}
    for row in products:
        name = row['Product']
        product_data[name] = {
            'price': float(row['Price_per_pack']),
            'grains': float(row['Grains_per_pack']),
            'meat': float(row['Meat_per_pack']),
            'variable_cost': float(row['Variable_cost_per_pack']),
            'capacity': float(row['Production_capacity']) if row['Production_capacity'].strip() else None
        }
    
    # Build LP model using PuLP
    import gurobi_pulp_compat as pulp
    
    prob = pulp.LpProblem("HealthyPetFoods", pulp.LpMaximize)
    
    # Decision variables: number of packs produced
    x_meaties = pulp.LpVariable("Meaties", lowBound=0)
    x_yummies = pulp.LpVariable("Yummies", lowBound=0)
    
    # Profit per pack = selling price - variable cost - raw material cost per pack
    # Raw material cost per pack:
    #   Meaties: grains_per_pack * price_grains + meat_per_pack * price_meat
    #   Yummies: grains_per_pack * price_grains + meat_per_pack * price_meat
    
    m = product_data['Meaties']
    y = product_data['Yummies']
    
    profit_meaties = m['price'] - m['variable_cost'] - (m['grains'] * price_grains + m['meat'] * price_meat)
    profit_yummies = y['price'] - y['variable_cost'] - (y['grains'] * price_grains + y['meat'] * price_meat)
    
    print(f"Profit per pack Meaties: {profit_meaties}")
    print(f"Profit per pack Yummies: {profit_yummies}")
    
    # Objective: maximize total profit
    prob += profit_meaties * x_meaties + profit_yummies * x_yummies, "Total_Profit"
    
    # Constraints
    # Grains availability
    prob += m['grains'] * x_meaties + y['grains'] * x_yummies <= max_grains, "Grains_Constraint"
    
    # Meat availability
    prob += m['meat'] * x_meaties + y['meat'] * x_yummies <= max_meat, "Meat_Constraint"
    
    # Production capacity for Meaties
    if m['capacity'] is not None:
        prob += x_meaties <= m['capacity'], "Meaties_Capacity"
    
    # Production capacity for Yummies (if any)
    if y['capacity'] is not None:
        prob += x_yummies <= y['capacity'], "Yummies_Capacity"
    
    # Solve
    prob.solve(pulp.GUROBI_CMD(msg=0))
    
    print(f"Status: {pulp.LpStatus[prob.status]}")
    print(f"Meaties: {x_meaties.varValue}")
    print(f"Yummies: {x_yummies.varValue}")
    
    obj_val = pulp.value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()