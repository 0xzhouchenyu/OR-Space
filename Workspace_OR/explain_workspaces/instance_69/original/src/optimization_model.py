import os
import pandas as pd
import gurobi_pulp_compat as pulp

def solve():
    data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'general_parameters.csv')
    df = pd.read_csv(data_path)
    
    params = {}
    for _, row in df.iterrows():
        params[row['Parameter_Name']] = row['Value']
        
    q3 = int(params['batch_3m_quantity'])
    q4 = int(params['batch_4m_quantity'])
    L = int(params['raw_bar_length'])
    
    # Lengths of the two types of steel bars
    len1 = 3
    len2 = 4
    
    # Generate all valid cutting patterns
    patterns = []
    for x in range(L // len1 + 1):
        for y in range(L // len2 + 1):
            if len1 * x + len2 * y <= L:
                if x > 0 or y > 0:
                    patterns.append((x, y))
                    
    prob = pulp.LpProblem("CuttingStock", pulp.LpMinimize)
    
    # Decision variables: number of times each pattern is used
    vars = pulp.LpVariable.dicts("Pattern", range(len(patterns)), lowBound=0, cat='Integer')
    
    # Objective: minimize total waste
    # Total waste = (Total length of raw bars used) - (Total length of required pieces)
    # Note: Any overproduced pieces are also considered waste.
    prob += pulp.lpSum([L * vars[i] for i in range(len(patterns))]) - (len1 * q3 + len2 * q4)
    
    # Constraints: satisfy the demand for each type of steel bar
    prob += pulp.lpSum([patterns[i][0] * vars[i] for i in range(len(patterns))]) >= q3
    prob += pulp.lpSum([patterns[i][1] * vars[i] for i in range(len(patterns))]) >= q4
    
    # Solve the problem
    prob.solve(pulp.GUROBI_CMD(msg=False))
    
    obj_val = pulp.value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    solve()