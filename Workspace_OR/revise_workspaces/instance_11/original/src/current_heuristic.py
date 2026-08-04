import os
import pandas as pd
import gurobi_pulp_compat as pulp

def solve():
    # Define paths
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    table_1_path = os.path.join(data_dir, 'table_1.csv')
    params_path = os.path.join(data_dir, 'general_parameters.csv')
    
    # Read CSVs
    df1 = pd.read_csv(table_1_path)
    df_params = pd.read_csv(params_path)
    
    # Parse Table 1
    row_a = df1[df1['Type'] == 'Type_A'].iloc[0]
    row_b = df1[df1['Type'] == 'Type_B'].iloc[0]
    row_cap = df1[df1['Type'] == 'Max_weekly_capacity'].iloc[0]
    row_cost = df1[df1['Type'] == 'Process_cost_Yuan_per_hour'].iloc[0]
    
    mfg_a = float(row_a['Manufacturing_hours_per_unit'])
    asm_a = float(row_a['Assembly_hours_per_unit'])
    insp_a = float(row_a['Inspection_hours_per_unit'])
    price_a = float(row_a['Selling_Price_Yuan_per_unit'])
    
    mfg_b = float(row_b['Manufacturing_hours_per_unit'])
    asm_b = float(row_b['Assembly_hours_per_unit'])
    insp_b = float(row_b['Inspection_hours_per_unit'])
    price_b = float(row_b['Selling_Price_Yuan_per_unit'])
    
    cap_mfg = float(row_cap['Manufacturing_hours_per_unit'])
    cap_asm = float(row_cap['Assembly_hours_per_unit'])
    cap_insp = float(row_cap['Inspection_hours_per_unit'])
    
    cost_mfg = float(row_cost['Manufacturing_hours_per_unit'])
    cost_asm = float(row_cost['Assembly_hours_per_unit'])
    cost_insp = float(row_cost['Inspection_hours_per_unit'])
    
    # Parse Parameters
    min_profit = float(df_params[df_params['Parameter_Name'] == 'min_weekly_profit']['Value'].iloc[0])
    min_a = float(df_params[df_params['Parameter_Name'] == 'min_type_a_production']['Value'].iloc[0])
    
    # Calculate Unit Profits
    cost_a = mfg_a * cost_mfg + asm_a * cost_asm + insp_a * cost_insp
    profit_a = price_a - cost_a
    
    cost_b = mfg_b * cost_mfg + asm_b * cost_asm + insp_b * cost_insp
    profit_b = price_b - cost_b
    
    # Step 1: Minimize Weighted Idle Time
    prob1 = pulp.LpProblem("Minimize_Idle_Time", pulp.LpMinimize)
    
    x_A = pulp.LpVariable('x_A', lowBound=min_a, cat='Integer')
    x_B = pulp.LpVariable('x_B', lowBound=0, cat='Integer')
    
    # Capacity Constraints
    prob1 += mfg_a * x_A + mfg_b * x_B <= cap_mfg
    prob1 += asm_a * x_A + asm_b * x_B <= cap_asm
    prob1 += insp_a * x_A + insp_b * x_B <= cap_insp
    
    # Profit Constraint
    prob1 += profit_a * x_A + profit_b * x_B >= min_profit
    
    # Objective 1
    idle_mfg = cap_mfg - (mfg_a * x_A + mfg_b * x_B)
    idle_asm = cap_asm - (asm_a * x_A + asm_b * x_B)
    idle_insp = cap_insp - (insp_a * x_A + insp_b * x_B)
    
    weighted_idle = cost_mfg * idle_mfg + cost_asm * idle_asm + cost_insp * idle_insp
    prob1 += weighted_idle
    
    prob1.solve(pulp.GUROBI_CMD(msg=False))
    min_idle_val = pulp.value(prob1.objective)
    
    # Step 2: Maximize Profit subject to minimum idle time
    # This lexicographic approach ensures we find the solution that minimizes idle time 
    # while outputting its profit as the final objective value.
    prob2 = pulp.LpProblem("Maximize_Profit", pulp.LpMaximize)
    
    x_A2 = pulp.LpVariable('x_A2', lowBound=min_a, cat='Integer')
    x_B2 = pulp.LpVariable('x_B2', lowBound=0, cat='Integer')
    
    # Capacity Constraints
    prob2 += mfg_a * x_A2 + mfg_b * x_B2 <= cap_mfg
    prob2 += asm_a * x_A2 + asm_b * x_B2 <= cap_asm
    prob2 += insp_a * x_A2 + insp_b * x_B2 <= cap_insp
    
    # Profit Constraint
    prob2 += profit_a * x_A2 + profit_b * x_B2 >= min_profit
    
    # Idle Time Constraint
    idle_mfg2 = cap_mfg - (mfg_a * x_A2 + mfg_b * x_B2)
    idle_asm2 = cap_asm - (asm_a * x_A2 + asm_b * x_B2)
    idle_insp2 = cap_insp - (insp_a * x_A2 + insp_b * x_B2)
    
    weighted_idle2 = cost_mfg * idle_mfg2 + cost_asm * idle_asm2 + cost_insp * idle_insp2
    prob2 += weighted_idle2 <= min_idle_val + 1e-5
    
    # Objective 2
    prob2 += profit_a * x_A2 + profit_b * x_B2
    
    prob2.solve(pulp.GUROBI_CMD(msg=False))
    
    final_obj = pulp.value(prob2.objective)
    print(f"OBJECTIVE_VALUE: {round(final_obj, 4)}")

if __name__ == '__main__':
    solve()