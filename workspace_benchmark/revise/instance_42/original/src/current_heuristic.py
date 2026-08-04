import os
import gurobi_pulp_compat as pulp
from utils import load_parameters

def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    params = load_parameters(os.path.join(data_dir, 'general_parameters.csv'))
    
    a = params['a']  # hours per furnace, method 1
    m = params['m']  # cost per furnace, method 1
    b = params['b']  # hours per furnace, method 2
    n = params['n']  # cost per furnace, method 2
    k = params['k']  # tons per furnace use
    d = params['d']  # minimum production
    c = params['c']  # max time available
    
    # Decision variables: x_ij = number of times furnace i uses method j
    prob = pulp.LpProblem("SteelFurnace", pulp.LpMinimize)
    
    x1 = pulp.LpVariable("x1", lowBound=0)  # furnace 1, method 1
    x2 = pulp.LpVariable("x2", lowBound=0)  # furnace 1, method 2
    x3 = pulp.LpVariable("x3", lowBound=0)  # furnace 2, method 1
    x4 = pulp.LpVariable("x4", lowBound=0)  # furnace 2, method 2
    
    # Objective: minimize fuel cost
    prob += m * (x1 + x3) + n * (x2 + x4), "TotalFuelCost"
    
    # Time constraints for each furnace
    prob += a * x1 + b * x2 <= c, "Furnace1_Time"
    prob += a * x3 + b * x4 <= c, "Furnace2_Time"
    
    # Minimum production requirement
    prob += k * (x1 + x2 + x3 + x4) >= d, "MinProduction"
    
    prob.solve(pulp.GUROBI_CMD(msg=0))
    
    obj_val = pulp.value(prob.objective)
    print(f"Status: {pulp.LpStatus[prob.status]}")
    print(f"x1={x1.varValue}, x2={x2.varValue}, x3={x3.varValue}, x4={x4.varValue}")
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()