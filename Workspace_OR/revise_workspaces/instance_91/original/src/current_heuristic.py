import os
import gurobi_pulp_compat as pulp
from utils import load_parameters

def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    params = load_parameters(os.path.join(data_dir, 'general_parameters.csv'))
    
    profit_A = params['profit_product_A']
    profit_B = params['profit_product_B']
    assembly_time_A = params['assembly_time_A']
    assembly_time_B = params['assembly_time_B']
    machine_working_time_hours = params['machine_working_time']
    machine_working_time_minutes = machine_working_time_hours * 60  # convert to minutes
    
    # Production ratio: "at least 2 units of B for every 5 units of A"
    # This means B >= (2/5)*A, or equivalently 2A - 5B <= 0
    ratio_A = 5
    ratio_B = 2
    
    # Define the LP problem
    prob = pulp.LpProblem("Product_Mix", pulp.LpMaximize)
    
    # Decision variables (continuous, non-negative)
    A = pulp.LpVariable("Product_A", lowBound=0, cat='Continuous')
    B = pulp.LpVariable("Product_B", lowBound=0, cat='Continuous')
    
    # Objective function: maximize profit
    prob += profit_A * A + profit_B * B, "Total_Profit"
    
    # Constraint 1: Machine working time
    prob += assembly_time_A * A + assembly_time_B * B <= machine_working_time_minutes, "Machine_Time"
    
    # Constraint 2: Production ratio - at least 2 units of B for every 5 units of A
    # B >= (2/5) * A  =>  2A - 5B <= 0
    prob += ratio_B * A - ratio_A * B <= 0, "Production_Ratio"
    
    # Solve
    prob.solve(pulp.GUROBI_CMD(msg=0))
    
    print(f"Status: {pulp.LpStatus[prob.status]}")
    print(f"Product A: {pulp.value(A):.4f}")
    print(f"Product B: {pulp.value(B):.4f}")
    
    obj_val = pulp.value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj_val:.1f}")

if __name__ == "__main__":
    main()