import os
import csv
from gurobi_pulp_compat import *

def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    
    # Read parameters
    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name'].strip()] = float(row['Value'].strip())
    
    profit_corn = params['profit_per_acre_corn']
    profit_wheat = params['profit_per_acre_wheat']
    profit_soybeans = params['profit_per_acre_soybeans']
    profit_sorghum = params['profit_per_acre_sorghum']
    total_area = params['total_farm_area']
    corn_wheat_ratio = params['corn_wheat_ratio']
    soybeans_sorghum_ratio = params['soybeans_sorghum_ratio']
    wheat_sorghum_ratio = params['wheat_sorghum_ratio']
    
    # Decision variables
    prob = LpProblem("Farm_Optimization", LpMaximize)
    
    corn = LpVariable("corn", lowBound=0)
    wheat = LpVariable("wheat", lowBound=0)
    soybeans = LpVariable("soybeans", lowBound=0)
    sorghum = LpVariable("sorghum", lowBound=0)
    
    # Objective: maximize profit
    prob += profit_corn * corn + profit_wheat * wheat + profit_soybeans * soybeans + profit_sorghum * sorghum
    
    # Constraints
    # Total area
    prob += corn + wheat + soybeans + sorghum <= total_area, "total_area"
    
    # Corn >= 2 * wheat
    prob += corn >= corn_wheat_ratio * wheat, "corn_wheat_ratio"
    
    # Soybeans >= 0.5 * sorghum
    prob += soybeans >= soybeans_sorghum_ratio * sorghum, "soybeans_sorghum_ratio"
    
    # Wheat = 3 * sorghum (equality constraint based on "must be three times")
    prob += wheat == wheat_sorghum_ratio * sorghum, "wheat_sorghum_ratio"
    
    # Solve
    prob.solve(GUROBI_CMD(msg=0))
    
    print(f"Status: {LpStatus[prob.status]}")
    print(f"Corn: {corn.varValue:.2f} acres")
    print(f"Wheat: {wheat.varValue:.2f} acres")
    print(f"Soybeans: {soybeans.varValue:.2f} acres")
    print(f"Sorghum: {sorghum.varValue:.2f} acres")
    
    obj_val = value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()