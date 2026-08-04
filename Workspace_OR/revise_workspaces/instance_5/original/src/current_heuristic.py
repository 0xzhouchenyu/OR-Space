import gurobi_pulp_compat as pulp
import pandas as pd
import os

def solve():
    # Load data
    table_1_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'table_1.csv')
    params_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'general_parameters.csv')
    
    df = pd.read_csv(table_1_path)
    params = pd.read_csv(params_path)
    
    budget = float(params[params['Parameter_Name'] == 'budget']['Value'].iloc[0])
    food_intake = float(params[params['Parameter_Name'] == 'food_intake']['Value'].iloc[0])
    
    # Fill missing fiber content with 0
    df['Fiber_Content_per_100g'] = df['Fiber_Content_per_100g'].fillna(0)
    
    foods = df['Food'].tolist()
    types = df.set_index('Food')['Type'].to_dict()
    fiber = df.set_index('Food')['Fiber_Content_per_100g'].to_dict()
    price = df.set_index('Food')['Price_per_100g'].to_dict()
    
    # Create problem
    prob = pulp.LpProblem("Maximize_Fiber", pulp.LpMaximize)
    
    # Variables: x is amount in 100g units
    x = pulp.LpVariable.dicts("x", foods, lowBound=0, cat='Continuous')
    y = pulp.LpVariable.dicts("y", foods, cat='Binary')
    
    # Objective: maximize fiber
    prob += pulp.lpSum(fiber[f] * x[f] for f in foods)
    
    # Constraints
    # Total food intake (converted to 100g units)
    prob += pulp.lpSum(x[f] for f in foods) == food_intake / 100.0
    
    # Budget constraint
    prob += pulp.lpSum(price[f] * x[f] for f in foods) <= budget
    
    # Exactly one protein source
    proteins = [f for f in foods if types[f] == 'protein']
    prob += pulp.lpSum(y[f] for f in proteins) == 1
    
    # At least two kinds of vegetables
    vegetables = [f for f in foods if types[f] == 'vegetable']
    prob += pulp.lpSum(y[f] for f in vegetables) >= 2
    
    # Linking constraints and minimum inclusion amount (0.1 units of 100g = 10g)
    M = food_intake / 100.0
    for f in foods:
        prob += x[f] >= 0.1 * y[f]
        prob += x[f] <= M * y[f]
        
    # Solve the problem
    prob.solve(pulp.GUROBI_CMD(msg=False))
    
    return round(pulp.value(prob.objective), 4)

if __name__ == '__main__':
    print(f"OBJECTIVE_VALUE: {solve()}")