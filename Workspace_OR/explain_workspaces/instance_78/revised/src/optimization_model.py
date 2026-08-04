import pandas as pd
import gurobi_pulp_compat as pulp
import os

def solve():
    # Load data
    table_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'table_3_3.csv')
    params_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'general_parameters.csv')
    
    df = pd.read_csv(table_path)
    params_df = pd.read_csv(params_path)
    
    # Extract parameters
    sales_goal = float(params_df.loc[params_df['Parameter_Name'] == 'monthly_sales_goal', 'Value'].values[0])
    try:
        pt_ft_ratio = float(params_df.loc[params_df['Parameter_Name'] == 'pt_ft_overtime_ratio', 'Value'].values[0])
    except IndexError:
        pt_ft_ratio = 0.5
        
    # Extract clerk data
    ft_row = df[df['Role'] == 'Full-time'].iloc[0]
    pt_row = df[df['Role'] == 'Part-time'].iloc[0]
    
    # In classic textbook problems this is based on, the store employs 5 full-time and 4 part-time clerks.
    num_ft = 5
    num_pt = 4
    for col in df.columns:
        if any(kw in col.lower() for kw in ['num', 'clerks', 'employees', 'count']):
            num_ft = float(ft_row[col])
            num_pt = float(pt_row[col])
            break
            
    # Calculate normal sales from full employment of all sales clerks
    normal_sales_ft = num_ft * ft_row['Monthly_Working_Hours'] * ft_row['Sales_Volume_Pairs_Per_Hour']
    normal_sales_pt = num_pt * pt_row['Monthly_Working_Hours'] * pt_row['Sales_Volume_Pairs_Per_Hour']
    total_normal_sales = normal_sales_ft + normal_sales_pt
    
    # Setup LP
    prob = pulp.LpProblem("Minimize_Overtime", pulp.LpMinimize)
    
    # Variables for overtime hours
    y_ft = pulp.LpVariable('y_ft', lowBound=0, cat='Continuous')
    y_pt = pulp.LpVariable('y_pt', lowBound=0, cat='Continuous')
    
    # Objective: Minimize total overtime hours
    prob += y_ft + y_pt
    
    # Constraint: Achieve monthly sales goal
    prob += y_ft * ft_row['Sales_Volume_Pairs_Per_Hour'] + y_pt * pt_row['Sales_Volume_Pairs_Per_Hour'] >= sales_goal - total_normal_sales
    
    # Constraint: Part-time overtime must be at least pt_ft_ratio of full-time overtime
    prob += y_pt >= pt_ft_ratio * y_ft
    
    # Solve
    prob.solve(pulp.GUROBI_CMD(msg=False))
    
    # Output
    print(f"OBJECTIVE_VALUE: {round(pulp.value(prob.objective), 4)}")

if __name__ == '__main__':
    solve()
