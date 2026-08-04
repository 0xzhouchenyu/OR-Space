import os
import csv
import gurobi_pulp_compat as pulp
from utils import load_csv_data

def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    
    table1 = load_csv_data(os.path.join(data_dir, 'table_1.csv'))
    params = load_csv_data(os.path.join(data_dir, 'general_parameters.csv'))
    
    param_dict = {}
    for row in params:
        param_dict[row['Parameter_Name']] = float(row['Value'])
    
    proc_I = table1[0]
    proc_II = table1[1]
    profit_row = table1[2]
    
    a_I = float(proc_I['Model_A_hours_per_unit'])
    b_I = float(proc_I['Model_B_hours_per_unit'])
    cap_I = float(proc_I['Maximum_Weekly_Processing_Capacity'])
    
    a_II = float(proc_II['Model_A_hours_per_unit'])
    b_II = float(proc_II['Model_B_hours_per_unit'])
    cap_II = float(proc_II['Maximum_Weekly_Processing_Capacity'])
    
    profit_A = float(profit_row['Model_A_hours_per_unit'])
    profit_B = float(profit_row['Model_B_hours_per_unit'])
    
    min_profit = param_dict['min_weekly_profit']
    min_A = param_dict['min_model_A_units']
    min_B = param_dict['min_model_B_units']
    proc_I_hours = param_dict['process_I_hours']
    max_overtime = param_dict['process_II_max_overtime']
    red_A = param_dict['model_A_overtime_profit_reduction']
    red_B = param_dict['model_B_overtime_profit_reduction']
    
    prob = pulp.LpProblem("Microcomputer_Production_Market_Share", pulp.LpMaximize)
    
    xA_r = pulp.LpVariable("xA_r", lowBound=0)
    xA_o = pulp.LpVariable("xA_o", lowBound=0)
    xB_r = pulp.LpVariable("xB_r", lowBound=0)
    xB_o = pulp.LpVariable("xB_o", lowBound=0)
    
    total_A = xA_r + xA_o
    total_B = xB_r + xB_o
    
    prob += a_I * total_A + b_I * total_B == proc_I_hours
    prob += a_II * xA_r + b_II * xB_r <= cap_II
    prob += a_II * xA_o + b_II * xB_o <= max_overtime
    prob += total_A >= min_A
    prob += total_B >= min_B
    
    total_profit = profit_A * xA_r + profit_B * xB_r + (profit_A - red_A) * xA_o + (profit_B - red_B) * xB_o
    prob += total_profit >= min_profit
    
    prob += total_A + total_B
    
    prob.solve(pulp.GUROBI_CMD(msg=0))
    
    obj_val = pulp.value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()