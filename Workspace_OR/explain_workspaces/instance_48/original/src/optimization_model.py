import os
import csv
from utils import load_csv_data

def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    
    table1 = load_csv_data(os.path.join(data_dir, 'table_1.csv'))
    params = load_csv_data(os.path.join(data_dir, 'general_parameters.csv'))
    
    # Parse parameters
    param_dict = {}
    for row in params:
        param_dict[row['Parameter_Name']] = float(row['Value'])
    
    # Parse table1
    proc_I = table1[0]
    proc_II = table1[1]
    profit_row = table1[2]
    
    a_I = float(proc_I['Model_A_hours_per_unit'])  # 4
    b_I = float(proc_I['Model_B_hours_per_unit'])  # 6
    cap_I = float(proc_I['Maximum_Weekly_Processing_Capacity'])  # 150
    
    a_II = float(proc_II['Model_A_hours_per_unit'])  # 3
    b_II = float(proc_II['Model_B_hours_per_unit'])  # 2
    cap_II = float(proc_II['Maximum_Weekly_Processing_Capacity'])  # 70
    
    profit_A = float(profit_row['Model_A_hours_per_unit'])  # 300
    profit_B = float(profit_row['Model_B_hours_per_unit'])  # 450
    
    min_profit = param_dict['min_weekly_profit']  # 10000
    min_A = param_dict['min_model_A_units']  # 10
    min_B = param_dict['min_model_B_units']  # 15
    proc_I_hours = param_dict['process_I_hours']  # 150
    max_overtime = param_dict['process_II_max_overtime']  # 30
    red_A = param_dict['model_A_overtime_profit_reduction']  # 20
    red_B = param_dict['model_B_overtime_profit_reduction']  # 25
    
    import gurobi_pulp_compat as pulp
    
    prob = pulp.LpProblem("Microcomputer_Production", pulp.LpMaximize)
    
    xA = pulp.LpVariable("xA", lowBound=0)
    xB = pulp.LpVariable("xB", lowBound=0)
    ot = pulp.LpVariable("overtime", lowBound=0, upBound=max_overtime)
    
    # Process I exact constraint
    prob += a_I * xA + b_I * xB == proc_I_hours
    
    # Process II: base + overtime
    prob += a_II * xA + b_II * xB <= cap_II + ot
    
    # Minimum production
    prob += xA >= min_A
    prob += xB >= min_B
    
    # Profit with overtime penalty proportional to overtime hours
    # Overtime fraction for each model: proportional allocation
    # Profit = 300*xA + 450*xB - (20*xA + 25*xB) * (ot / (3*xA + 2*xB)) -- nonlinear
    # Alternative: penalty per overtime hour
    # Use linear approximation: penalty = red_A * (a_II portion) + red_B * (b_II portion) per overtime hour
    # Weighted average penalty per overtime hour = (20*3*xA + 25*2*xB)/(3xA+2xB) -- nonlinear
    
    # Simpler: let's define regular and overtime production separately
    # xA = xA_r + xA_o, xB = xB_r + xB_o
    
    prob2 = pulp.LpProblem("Microcomputer_Production2", pulp.LpMaximize)
    
    xA_r = pulp.LpVariable("xA_r", lowBound=0)
    xA_o = pulp.LpVariable("xA_o", lowBound=0)
    xB_r = pulp.LpVariable("xB_r", lowBound=0)
    xB_o = pulp.LpVariable("xB_o", lowBound=0)
    
    total_A = xA_r + xA_o
    total_B = xB_r + xB_o
    
    # Process I exact
    prob2 += a_I * (total_A) + b_I * (total_B) == proc_I_hours
    
    # Process II regular capacity
    prob2 += a_II * xA_r + b_II * xB_r <= cap_II
    
    # Process II overtime capacity
    prob2 += a_II * xA_o + b_II * xB_o <= max_overtime
    
    # Minimum production
    prob2 += total_A >= min_A
    prob2 += total_B >= min_B
    
    # Profit
    total_profit = profit_A * xA_r + profit_B * xB_r + (profit_A - red_A) * xA_o + (profit_B - red_B) * xB_o
    
    # Min profit goal
    prob2 += total_profit >= min_profit
    
    prob2 += total_profit
    
    prob2.solve(pulp.GUROBI_CMD(msg=0))
    
    obj_val = pulp.value(prob2.objective)
    
    print(f"xA_regular = {pulp.value(xA_r)}")
    print(f"xA_overtime = {pulp.value(xA_o)}")
    print(f"xB_regular = {pulp.value(xB_r)}")
    print(f"xB_overtime = {pulp.value(xB_o)}")
    print(f"Total A = {pulp.value(xA_r) + pulp.value(xA_o)}")
    print(f"Total B = {pulp.value(xB_r) + pulp.value(xB_o)}")
    print(f"Process II regular hours = {a_II*pulp.value(xA_r) + b_II*pulp.value(xB_r)}")
    print(f"Process II overtime hours = {a_II*pulp.value(xA_o) + b_II*pulp.value(xB_o)}")
    
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()