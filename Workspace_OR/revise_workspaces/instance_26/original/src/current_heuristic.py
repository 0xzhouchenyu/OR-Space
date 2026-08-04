import os
import csv
from gurobi_pulp_compat import *

def main():
    # Load data
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    
    # Read staffing requirements
    requirements = {}
    with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            period = row['Time_Period'].strip()
            req = int(row['Required_Salespeople'].strip())
            requirements[period] = req
    
    # The time periods and their requirements in order
    # Periods: 0: 2-6, 1: 6-10, 2: 10-14, 3: 14-18, 4: 18-22, 5: 22-2
    periods = list(requirements.keys())
    req_values = list(requirements.values())
    n = len(periods)  # 6 periods
    
    # Each shift is 8 hours = 2 consecutive periods
    # Shift i starts at the beginning of period i and covers periods i and (i+1) % n
    # Decision variables: x_i = number of salespeople starting shift at period i
    
    prob = LpProblem("MinSalespeople", LpMinimize)
    
    # Decision variables
    x = [LpVariable(f"x_{i}", lowBound=0, cat='Integer') for i in range(n)]
    
    # Objective: minimize total salespeople
    prob += lpSum(x)
    
    # Constraints: for each period j, the salespeople working during period j
    # are those who started in period j or period (j-1) % n
    # (since each shift covers 2 consecutive periods)
    for j in range(n):
        prob += x[j] + x[(j - 1) % n] >= req_values[j], f"demand_{j}"
    
    # Solve
    prob.solve(GUROBI_CMD(msg=0))
    
    obj_val = value(prob.objective)
    
    # Print solution details
    for i in range(n):
        print(f"Shift starting at period {periods[i]}: {int(value(x[i]))} salespeople")
    
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()