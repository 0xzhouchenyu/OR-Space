import os
import sys
from utils import load_parameters
import gurobi_pulp_compat as pulp

def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    params = load_parameters(os.path.join(data_dir, 'general_parameters.csv'))
    
    rc_a = params['refrigerated_capacity_type_a']
    nc_a = params['non_refrigerated_capacity_type_a']
    rc_b = params['refrigerated_capacity_type_b']
    nc_b = params['non_refrigerated_capacity_type_b']
    ref_req = params['refrigerated_cargo_requirement']
    nonref_req = params['non_refrigerated_cargo_requirement']
    cost_a = params['rental_cost_type_a']
    cost_b = params['rental_cost_type_b']
    
    # Create the optimization problem
    prob = pulp.LpProblem("TruckRental", pulp.LpMinimize)
    
    # Decision variables (integer, non-negative)
    x = pulp.LpVariable("TypeA_trucks", lowBound=0, cat='Integer')
    y = pulp.LpVariable("TypeB_trucks", lowBound=0, cat='Integer')
    
    # Objective: minimize total cost
    prob += cost_a * x + cost_b * y, "TotalCost"
    
    # Constraints
    prob += rc_a * x + rc_b * y >= ref_req, "RefrigeratedRequirement"
    prob += nc_a * x + nc_b * y >= nonref_req, "NonRefrigeratedRequirement"
    
    # Solve
    prob.solve(pulp.GUROBI_CMD(msg=0))
    
    obj_val = pulp.value(prob.objective)
    
    print(f"Type A trucks: {int(pulp.value(x))}")
    print(f"Type B trucks: {int(pulp.value(y))}")
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()