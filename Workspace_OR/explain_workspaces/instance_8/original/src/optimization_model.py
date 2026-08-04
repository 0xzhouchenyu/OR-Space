import os
import csv
from itertools import combinations
import gurobi_pulp_compat as pulp

def main():
    # Load data
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    
    # Read table_1.csv
    filepath = os.path.join(data_dir, 'table_1.csv')
    
    workers = []
    tasks = []
    cost = {}
    
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        tasks = header[1:]  # ['A', 'B', 'C', 'D']
        
        for row in reader:
            worker = row[0].strip()
            workers.append(worker)
            for j, task in enumerate(tasks):
                cost[(worker, task)] = int(row[j + 1])
    
    # Create the optimization model
    # We need to select 4 out of 5 workers and assign each to exactly one task
    # Minimize total time
    
    prob = pulp.LpProblem("Assignment", pulp.LpMinimize)
    
    # Decision variables: x[i,j] = 1 if worker i is assigned to task j
    x = {}
    for w in workers:
        for t in tasks:
            x[(w, t)] = pulp.LpVariable(f"x_{w}_{t}", cat='Binary')
    
    # Objective: minimize total cost
    prob += pulp.lpSum(cost[(w, t)] * x[(w, t)] for w in workers for t in tasks)
    
    # Each task must be assigned to exactly one worker
    for t in tasks:
        prob += pulp.lpSum(x[(w, t)] for w in workers) == 1
    
    # Each worker can be assigned to at most one task
    for w in workers:
        prob += pulp.lpSum(x[(w, t)] for t in tasks) <= 1
    
    # Exactly 4 workers are assigned (implied by 4 tasks each with exactly 1 worker,
    # but this is already enforced)
    
    # Solve
    prob.solve(pulp.GUROBI_CMD(msg=0))
    
    # Print solution details
    print("Status:", pulp.LpStatus[prob.status])
    print("\nAssignment:")
    for w in workers:
        for t in tasks:
            if pulp.value(x[(w, t)]) > 0.5:
                print(f"  Worker {w} -> Task {t} (time: {cost[(w, t)]})")
    
    obj_val = pulp.value(prob.objective)
    print(f"\nOBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()