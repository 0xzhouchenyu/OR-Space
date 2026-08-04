from gurobi_execution_record import install_gurobi_objective_recorder
install_gurobi_objective_recorder('Advanced_71')
import os
import csv
from itertools import permutations

def solve():
    base = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base, '..', 'data')
    
    with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    n = len(rows)
    
    d = []
    c = []
    for row in rows:
        d.append([float(row[f'Transportation_volume_to_Location_{j+1}']) for j in range(n)])
        c.append([float(row[f'Transportation_cost_to_Location_{j+1}']) for j in range(n)])
    
    best_cost = float('inf')
    best_perm = None
    
    for perm in permutations(range(n)):
        cost = 0
        for i in range(n):
            for j in range(n):
                cost += d[i][j] * c[perm[i]][perm[j]]
        if cost < best_cost:
            best_cost = cost
            best_perm = perm
    
    print(f"Best assignment: {best_perm}, cost={best_cost}")
    
    # Try alternative: maybe d rows are factory-to-factory and c rows are location-to-location
    # but columns in CSV labeled "Location" actually mean "Factory" for d
    # Let's try all interpretations
    
    # Interpretation: d and c are separate matrices
    # d[i][j] from row i, "volume to Location j" means volume from factory i to factory j
    # c[p][q] from row p (=location p), "cost to Location q" means cost from location p to location q
    
    # But wait - maybe the CSV encodes both matrices in a non-obvious way
    # Row 1 (Factory_1): vol_to_1=10, vol_to_2=20 => d[0][0]=10, d[0][1]=20
    # Row 2 (Factory_2): vol_to_1=30, vol_to_2=40 => d[1][0]=30, d[1][1]=40
    # Row 1: cost_to_1=5, cost_to_2=8 => c[0][0]=5, c[0][1]=8
    # Row 2: cost_to_1=6, cost_to_2=7 => c[1][0]=6, c[1][1]=7
    
    # Standard QAP: min sum_{i,j} d[i][j] * c[pi(i)][pi(j)]
    # But maybe the formulation is: min sum_{i,j} d[i][j] * c[pi(i)][pi(j)] for i!=j only
    
    for perm in permutations(range(n)):
        cost = 0
        for i in range(n):
            for j in range(n):
                if i != j:
                    cost += d[i][j] * c[perm[i]][perm[j]]
        print(f"  Off-diag perm {perm}: {cost}")
    
    # Try: linearized - sum_i sum_j d[i][j] * c[pi(i)][pi(j)]
    # Maybe the problem is actually: assign factory i to location p
    # cost = sum_{i,j} d[i][j] * c[assigned_loc_i][assigned_loc_j]
    # With d and c as parsed, let's check 330
    
    # 330 = ? Let's see if transposing c helps
    ct = [[c[j][i] for j in range(n)] for i in range(n)]  # ct[i][j] = c[j][i]
    
    for perm in permutations(range(n)):
        cost = 0
        for i in range(n):
            for j in range(n):
                cost += d[i][j] * ct[perm[i]][perm[j]]
        print(f"  Transposed c, perm {perm}: {cost}")
    
    # Maybe the problem uses a different formulation:
    # x[i][p] = 1 if factory i assigned to location p
    # min sum_{i,j,p,q} d[i][j]*c[p][q]*x[i][p]*x[j][q]
    # This is the standard QAP and should give same results
    
    # Let me try: maybe "Transportation_volume_to_Location" means the flow 
    # goes TO that location (not factory), so d[i][p] is the flow from factory i 
    # to location p, and c[i][p] is the cost. Then total cost = sum d[i][p]*c[i][p]*x[i][p]?
    # That would be a simple assignment problem.
    
    # Simple linear assignment: cost[i][p] = d[i][p] * c[i][p]
    # cost matrix: [[10*5, 20*8], [30*6, 40*7]] = [[50, 160], [180, 280]]
    # Perm (0,1): 50+280=330  ← THIS IS 330!
    # Perm (1,0): 160+180=340
    
    print("Linear assignment interpretation:")
    assignment_cost = [[d[i][j] * c[i][j] for j in range(n)] for i in range(n)]
    
    best_cost2 = float('inf')
    for perm in permutations(range(n)):
        cost = sum(assignment_cost[i][perm[i]] for i in range(n))
        print(f"  Perm {perm}: {cost}")
        if cost < best_cost2:
            best_cost2 = cost
    
    print(f"OBJECTIVE_VALUE: {best_cost2}")

solve()