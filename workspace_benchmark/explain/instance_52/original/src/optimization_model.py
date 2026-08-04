import os
import csv
from gurobi_pulp_compat import *

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, '..', 'data')
    
    # Read shift requirements
    shifts = []
    with open(os.path.join(data_dir, 'table_1_2.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            shifts.append({
                'shift': int(row['Shift']),
                'time': row['Time'],
                'required': int(row['Required_number'])
            })
    
    n = len(shifts)  # number of periods (6)
    required = [s['required'] for s in shifts]
    
    # Read general parameters
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Parameter_Name'] == 'shift_duration':
                shift_duration = int(row['Value'])  # 8 hours
    
    # Each time period is 4 hours, shift_duration is 8 hours = 2 periods
    periods_per_shift = shift_duration // 4  # = 2
    
    # Decision variables: x_i = number of workers starting at period i
    prob = LpProblem("MinimumWorkers", LpMinimize)
    
    x = [LpVariable(f"x_{i+1}", lowBound=0, cat='Integer') for i in range(n)]
    
    # Objective: minimize total workers
    prob += lpSum(x)
    
    # Constraints: for each period j, sum of workers starting at periods that cover j >= required[j]
    # A worker starting at period i covers periods i, i+1, ..., i+periods_per_shift-1 (mod n)
    for j in range(n):
        # Which starting periods cover period j?
        covering = []
        for i in range(n):
            # Worker starting at period i covers periods i, (i+1)%n, ..., (i+periods_per_shift-1)%n
            covered_periods = [(i + k) % n for k in range(periods_per_shift)]
            if j in covered_periods:
                covering.append(x[i])
        prob += lpSum(covering) >= required[j], f"Demand_period_{j+1}"
    
    prob.solve(GUROBI_CMD(msg=0))
    
    obj_val = value(prob.objective)
    
    # Print solution details
    for i in range(n):
        print(f"Workers starting at period {i+1}: {value(x[i])}")
    
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()