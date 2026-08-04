import os
import csv
from gurobi_pulp_compat import *

def main():
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    
    # Load table_1.csv
    table1_path = os.path.join(base_dir, 'table_1.csv')
    products = {}
    with open(table1_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            item = row['Item'].strip()
            products[item] = {
                'machine_time': float(row['Machine_Time_minutes'].strip()),
                'craftsman_time': float(row['Craftsman_Time_minutes'].strip())
            }
    
    # Load general_parameters.csv
    params_path = os.path.join(base_dir, 'general_parameters.csv')
    params = {}
    with open(params_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name'].strip()] = float(row['Value'].strip())
    
    machine_avail = params['machine_time_available']
    craftsman_reg_avail = params['craftsman_regular_time_available']
    craftsman_ot_avail = params['craftsman_overtime_available']
    machine_cost = params['machine_time_cost']
    craftsman_reg_cost = params['craftsman_time_cost']
    craftsman_ot_cost = params['craftsman_overtime_cost']
    rev_X = params['revenue_product_X']
    rev_Y = params['revenue_product_Y']
    min_X = params['min_batches_product_X']
    product_Y_QA_threshold = params['product_Y_QA_threshold']
    product_Y_QA_fee = params['product_Y_QA_fee']
    
    # Create LP problem
    prob = LpProblem("Production_Planning", LpMaximize)
    
    # Decision variables
    X = LpVariable("X", lowBound=0)
    Y = LpVariable("Y", lowBound=0)
    craft_reg = LpVariable("Craftsman_Regular_Hours", lowBound=0, upBound=craftsman_reg_avail)
    craft_ot = LpVariable("Craftsman_Overtime_Hours", lowBound=0, upBound=craftsman_ot_avail)
    product_Y_QA = LpVariable("product_Y_QA", cat='Binary')
    
    # Machine hours used and craftsman hours used
    machine_hours_used = (products['X']['machine_time'] * X + products['Y']['machine_time'] * Y) / 60.0
    craftsman_hours_used = (products['X']['craftsman_time'] * X + products['Y']['craftsman_time'] * Y) / 60.0
    
    # Objective: maximize revenue - costs
    profit = (rev_X * X + rev_Y * Y 
              - machine_cost * machine_hours_used 
              - craftsman_reg_cost * craft_reg 
              - craftsman_ot_cost * craft_ot
              - product_Y_QA_fee * product_Y_QA)
    prob += profit, "Total_Profit"
    
    # Constraints
    prob += machine_hours_used <= machine_avail, "Machine_Time_Constraint"
    prob += craftsman_hours_used == craft_reg + craft_ot, "Craftsman_Time_Balance"
    prob += X >= min_X, "Min_Production_X"
    prob += Y <= product_Y_QA_threshold + 10000 * product_Y_QA, "Product_Y_QA_Tier"
    
    # Solve
    prob.solve(GUROBI_CMD(msg=0))
    
    obj_val = value(prob.objective)
    
    print(f"OBJECTIVE_VALUE: {obj_val:.5f}")

if __name__ == "__main__":
    main()
