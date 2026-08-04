import gurobi_pulp_compat as pulp
from utils import load_data

def solve():
    df, prod_days = load_data()
    
    # Create problem
    prob = pulp.LpProblem("Production_Planning", pulp.LpMaximize)
    
    # Variables
    products = df['Product'].tolist()
    x = pulp.LpVariable.dicts("x", products, lowBound=0)
    y = pulp.LpVariable.dicts("y", products, cat='Binary')
    
    # Objective
    profit = pulp.lpSum([
        (row['Selling_Price'] - row['Production_Cost']) * x[row['Product']] - row['Activation_Cost'] * y[row['Product']] 
        for _, row in df.iterrows()
    ])
    prob += profit
    
    # Constraints
    # The company plans to produce all three types of products
    for p in products:
        prob += y[p] == 1
        
    for _, row in df.iterrows():
        p = row['Product']
        prob += x[p] <= row['Maximum_Demand'] * y[p]
        prob += x[p] >= row['Minimum_Batch'] * y[p]
        
    # Production days constraint
    prob += pulp.lpSum([x[row['Product']] / row['Production_Quota'] for _, row in df.iterrows()]) <= prod_days
    
    # Solve
    prob.solve(pulp.GUROBI_CMD(msg=False))
    
    return pulp.value(prob.objective)

if __name__ == "__main__":
    obj = solve()
    print(f"OBJECTIVE_VALUE: {round(obj, 4)}")