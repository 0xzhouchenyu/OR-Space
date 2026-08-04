import os
import gurobi_pulp_compat as pulp
from utils import load_restaurant_data, load_general_parameters

def main():
    # Determine data directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, '..', 'data')
    
    # Load data
    restaurants = load_restaurant_data(os.path.join(data_dir, 'table_1.csv'))
    params = load_general_parameters(os.path.join(data_dir, 'general_parameters.csv'))
    
    budget = params['investment_budget']
    
    # Create the optimization problem
    prob = pulp.LpProblem("Restaurant_Investment", pulp.LpMaximize)
    
    # Decision variables: binary (buy or not)
    x = {}
    for r in restaurants:
        x[r['name']] = pulp.LpVariable(f"x_{r['name']}", cat='Binary')
    
    # Objective: maximize total annual revenue
    prob += pulp.lpSum(r['revenue'] * x[r['name']] for r in restaurants), "Total_Annual_Revenue"
    
    # Budget constraint
    prob += pulp.lpSum(r['cost'] * x[r['name']] for r in restaurants) <= budget, "Budget_Constraint"
    
    # If Restaurant D is purchased, Restaurant A cannot be purchased
    # x_D + x_A <= 1
    if 'Restaurant_D' in x and 'Restaurant_A' in x:
        prob += x['Restaurant_D'] + x['Restaurant_A'] <= 1, "D_A_Exclusion_Constraint"
    
    # Solve
    prob.solve(pulp.GUROBI_CMD(msg=0))
    
    # Print results
    print(f"Status: {pulp.LpStatus[prob.status]}")
    for r in restaurants:
        val = pulp.value(x[r['name']])
        print(f"{r['name']}: {'Buy' if val > 0.5 else 'Do not buy'} (x={val})")
    
    obj_val = pulp.value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()