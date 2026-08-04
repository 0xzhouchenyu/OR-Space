import os
import csv
from gurobi_pulp_compat import *

def load_parameters():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    filepath = os.path.join(data_dir, 'general_parameters.csv')
    
    params = {}
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['Parameter_Name'].strip()
            value = row['Value'].strip()
            # Try to convert to number
            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    pass
            params[name] = value
    return params

def solve():
    params = load_parameters()
    
    # Extract parameters
    profit_robot = params['profit_per_robot']
    profit_car = params['profit_per_model_car']
    profit_blocks = params['profit_per_building_blocks']
    profit_doll = params['profit_per_doll']
    
    plastic_avail = params['plastic_available']
    plastic_robot = params['plastic_per_robot']
    plastic_car = params['plastic_per_model_car']
    plastic_blocks = params['plastic_per_building_blocks']
    plastic_doll = params['plastic_per_doll']
    
    # Big M for logical constraints
    M = 10000
    
    # Create problem
    prob = LpProblem("ToyManufacturing", LpMaximize)
    
    # Decision variables (integer, number of toys)
    x_robot = LpVariable("robots", lowBound=0, cat='Integer')
    x_car = LpVariable("model_cars", lowBound=0, cat='Integer')
    x_blocks = LpVariable("building_blocks", lowBound=0, cat='Integer')
    x_doll = LpVariable("dolls", lowBound=0, cat='Integer')
    
    # Binary variables for logical constraints
    y_robot = LpVariable("y_robot", cat='Binary')  # 1 if robots are manufactured
    y_doll = LpVariable("y_doll", cat='Binary')    # 1 if dolls are manufactured
    y_car = LpVariable("y_car", cat='Binary')      # 1 if model cars are manufactured
    y_blocks = LpVariable("y_blocks", cat='Binary') # 1 if building blocks are manufactured
    
    # Objective
    prob += profit_robot * x_robot + profit_car * x_car + profit_blocks * x_blocks + profit_doll * x_doll
    
    # Resource constraints
    prob += plastic_robot * x_robot + plastic_car * x_car + plastic_blocks * x_blocks + plastic_doll * x_doll <= plastic_avail, "Plastic"
    
    # Link binary variables to production quantities
    prob += x_robot <= M * y_robot, "Link_robot"
    prob += x_doll <= M * y_doll, "Link_doll"
    prob += x_car <= M * y_car, "Link_car"
    prob += x_blocks <= M * y_blocks, "Link_blocks"
    
    # If robots are manufactured, dolls cannot be manufactured (exclusion)
    prob += y_robot + y_doll <= 1, "Robot_Doll_Exclusion"
    
    # If model cars are manufactured, building blocks must also be manufactured
    prob += y_car <= y_blocks, "Car_Blocks_Dependency"
    
    # Dolls cannot exceed model cars
    prob += x_doll <= x_car, "Dolls_leq_Cars"
    
    # Fix: Ensure binary variables are correctly linked to production quantities
    prob += y_robot <= x_robot, "Binary_Link_Robot"
    prob += y_doll <= x_doll, "Binary_Link_Doll"
    prob += y_car <= x_car, "Binary_Link_Car"
    prob += y_blocks <= x_blocks, "Binary_Link_Blocks"
    
    # Solve
    prob.solve(GUROBI_CMD(msg=0))
    
    print(f"Status: {LpStatus[prob.status]}")
    print(f"Robots: {x_robot.varValue}")
    print(f"Model Cars: {x_car.varValue}")
    print(f"Building Blocks: {x_blocks.varValue}")
    print(f"Dolls: {x_doll.varValue}")
    
    obj_val = value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    solve()