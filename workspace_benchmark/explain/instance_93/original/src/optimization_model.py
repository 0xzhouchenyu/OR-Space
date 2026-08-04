import os
import csv
from gurobi_pulp_compat import *

def main():
    # Load data
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    
    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['Parameter_Name'].strip()
            val = row['Value'].strip()
            params[name] = val
    
    # Extract parameters
    a1_yield = float(params['product_A1_yield'])       # 3 kg per barrel
    a1_time = float(params['product_A1_time'])          # 12 hours per barrel
    a2_yield = float(params['product_A2_yield'])        # 4 kg per barrel
    a2_time = float(params['product_A2_time'])          # 8 hours per barrel
    profit_a1 = float(params['profit_per_kg_A1'])       # 24 yuan/kg
    profit_a2 = float(params['profit_per_kg_A2'])       # 16 yuan/kg
    milk_supply = float(params['daily_milk_supply'])     # 50 barrels
    labor_hours = float(params['daily_labor_hours'])     # 480 hours
    type_a_cap = float(params['type_A_capacity'])        # 100 kg
    
    # Profit per barrel
    profit_per_barrel_a1 = a1_yield * profit_a1  # 3 * 24 = 72
    profit_per_barrel_a2 = a2_yield * profit_a2  # 4 * 16 = 64
    
    # Decision variables: x1, x2 = barrels of milk for A1, A2
    prob = LpProblem("Dairy_Production", LpMaximize)
    
    x1 = LpVariable("x1", lowBound=0)  # barrels for A1
    x2 = LpVariable("x2", lowBound=0)  # barrels for A2
    
    # Objective: maximize profit
    prob += profit_per_barrel_a1 * x1 + profit_per_barrel_a2 * x2, "Total_Profit"
    
    # Constraints
    # Milk supply
    prob += x1 + x2 <= milk_supply, "Milk_Supply"
    
    # Labor hours (each barrel of A1 takes a1_time hours, each barrel of A2 takes a2_time hours)
    prob += a1_time * x1 + a2_time * x2 <= labor_hours, "Labor_Hours"
    
    # Type A equipment capacity (kg of A1 produced)
    prob += a1_yield * x1 <= type_a_cap, "Type_A_Capacity"
    
    # Solve
    prob.solve(GUROBI_CMD(msg=0))
    
    obj_val = value(prob.objective)
    
    print(f"Status: {LpStatus[prob.status]}")
    print(f"x1 (barrels for A1) = {value(x1)}")
    print(f"x2 (barrels for A2) = {value(x2)}")
    print(f"A1 produced = {value(x1) * a1_yield} kg")
    print(f"A2 produced = {value(x2) * a2_yield} kg")
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()