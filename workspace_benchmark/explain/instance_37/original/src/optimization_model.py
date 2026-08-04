import os
import csv
from gurobi_pulp_compat import *

def main():
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    
    # Load table_1.csv
    table1_path = os.path.join(base_dir, 'table_1.csv')
    with open(table1_path, 'r') as f:
        reader = csv.reader(f)
        headers = next(reader)
        rows = []
        for row in reader:
            rows.append(row)
    
    # Parse process data
    # Row 0: Process I, Row 1: Process II, Row 2: Profit_per_unit
    a_I = float(rows[0][1])  # Model A hours for Process I
    b_I = float(rows[0][2])  # Model B hours for Process I
    cap_I = float(rows[0][3])  # Max weekly capacity Process I
    
    a_II = float(rows[1][1])  # Model A hours for Process II
    b_II = float(rows[1][2])  # Model B hours for Process II
    cap_II = float(rows[1][3])  # Max weekly capacity Process II
    
    profit_A = float(rows[2][1])  # Profit per unit Model A
    profit_B = float(rows[2][2])  # Profit per unit Model B
    
    # Load general_parameters.csv
    params_path = os.path.join(base_dir, 'general_parameters.csv')
    params = {}
    with open(params_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name']] = float(row['Value'])
    
    min_profit = params['min_weekly_profit']
    min_A = params['min_model_A_units']
    min_B = params['min_model_B_units']
    
    # Create LP problem - Maximize profit
    prob = LpProblem("Microcomputer_Production", LpMaximize)
    
    # Decision variables (continuous - can produce fractional units)
    x_A = LpVariable("x_A", lowBound=0)
    x_B = LpVariable("x_B", lowBound=0)
    
    # Objective: Maximize profit
    prob += profit_A * x_A + profit_B * x_B, "Total_Profit"
    
    # Constraints
    # Process I capacity
    prob += a_I * x_A + b_I * x_B <= cap_I, "Process_I_Capacity"
    # Process II capacity
    prob += a_II * x_A + b_II * x_B <= cap_II, "Process_II_Capacity"
    # Minimum production requirements
    prob += x_A >= min_A, "Min_Model_A"
    prob += x_B >= min_B, "Min_Model_B"
    # Minimum profit constraint
    prob += profit_A * x_A + profit_B * x_B >= min_profit, "Min_Profit"
    
    # Solve
    prob.solve(GUROBI_CMD(msg=0))
    
    obj_val = value(prob.objective)
    print(f"Status: {LpStatus[prob.status]}")
    print(f"x_A = {value(x_A)}")
    print(f"x_B = {value(x_B)}")
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()