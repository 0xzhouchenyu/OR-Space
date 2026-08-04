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
    
    machine_avail = params['machine_time_available']  # hours
    craftsman_avail = params['craftsman_time_available']  # hours
    machine_cost = params['machine_time_cost']  # GBP per hour
    craftsman_cost = params['craftsman_time_cost']  # GBP per hour
    rev_X = params['revenue_product_X']  # GBP per batch
    rev_Y = params['revenue_product_Y']  # GBP per batch
    min_X = params['min_batches_product_X']  # batches
    
    # Create LP problem
    prob = LpProblem("Production_Planning", LpMaximize)
    
    # Decision variables (continuous, non-negative)
    X = LpVariable("X", lowBound=0)
    Y = LpVariable("Y", lowBound=0)
    
    # Machine hours used and craftsman hours used
    machine_hours_used = (products['X']['machine_time'] * X + products['Y']['machine_time'] * Y) / 60.0
    craftsman_hours_used = (products['X']['craftsman_time'] * X + products['Y']['craftsman_time'] * Y) / 60.0
    
    # Objective: maximize revenue - costs
    profit = rev_X * X + rev_Y * Y - machine_cost * machine_hours_used - craftsman_cost * craftsman_hours_used
    prob += profit, "Total_Profit"
    
    # Constraints
    prob += machine_hours_used <= machine_avail, "Machine_Time_Constraint"
    prob += craftsman_hours_used <= craftsman_avail, "Craftsman_Time_Constraint"
    prob += X >= min_X, "Min_Production_X"
    
    # Solve
    prob.solve(GUROBI_CMD(msg=0))
    
    obj_val = value(prob.objective)
    
    print(f"Status: {LpStatus[prob.status]}")
    print(f"X = {value(X):.4f}")
    print(f"Y = {value(Y):.4f}")
    print(f"OBJECTIVE_VALUE: {obj_val:.2f}")

if __name__ == "__main__":
    main()