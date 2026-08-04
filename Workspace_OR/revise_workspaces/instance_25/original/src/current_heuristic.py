import os
import csv
from utils import load_parameters

try:
    import gurobi_pulp_compat as pulp
except ImportError:
    pulp = None

def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    params = load_parameters(os.path.join(data_dir, 'general_parameters.csv'))
    
    W = params['initial_investment']       # 100000
    r1 = params['return_rate_option_1']    # 0.7
    r2 = params['return_rate_option_2']    # 2.0
    T = int(params['planning_horizon'])    # 3
    
    # Decision variables:
    # x0_1: amount invested in Option 1 at year 0
    # x0_2: amount invested in Option 2 at year 0
    # x1_1: amount invested in Option 1 at year 1
    # x1_2: amount invested in Option 2 at year 1
    # x2_1: amount invested in Option 1 at year 2
    
    prob = pulp.LpProblem("Investment", pulp.LpMaximize)
    
    x0_1 = pulp.LpVariable("x0_1", lowBound=0)
    x0_2 = pulp.LpVariable("x0_2", lowBound=0)
    x1_1 = pulp.LpVariable("x1_1", lowBound=0)
    x1_2 = pulp.LpVariable("x1_2", lowBound=0)
    x2_1 = pulp.LpVariable("x2_1", lowBound=0)
    
    # Year 0 budget constraint
    prob += x0_1 + x0_2 <= W, "year0_budget"
    
    # Year 1: money available = returns from x0_1 = x0_1 * (1 + r1)
    prob += x1_1 + x1_2 <= x0_1 * (1 + r1), "year1_budget"
    
    # Year 2: money available = returns from x1_1 + returns from x0_2
    prob += x2_1 <= x1_1 * (1 + r1) + x0_2 * (1 + r2), "year2_budget"
    
    # Year 3 (end): total money = returns from x2_1 + returns from x1_2 + any uninvested cash
    # We want to maximize total wealth at year 3
    # Wealth at year 3 = x2_1*(1+r1) + x1_2*(1+r2) + leftover cash carried through
    # But to maximize, all money should be invested, so leftovers are 0 at optimum.
    # For completeness, let's track it properly with slack variables implicitly via LP.
    
    prob += x2_1 * (1 + r1) + x1_2 * (1 + r2), "objective"
    
    prob.solve(pulp.GUROBI_CMD(msg=0))
    
    obj_val = pulp.value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()