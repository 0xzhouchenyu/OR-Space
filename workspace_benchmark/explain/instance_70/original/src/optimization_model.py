from gurobi_execution_record import install_gurobi_objective_recorder
install_gurobi_objective_recorder('Advanced_70_exact_route')
import os
import sys
from itertools import permutations
from utils import load_distance_matrix

def solve_tsp():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    dist_file = os.path.join(data_dir, 'table_1.csv')
    
    cities, dist = load_distance_matrix(dist_file)
    n = len(cities)
    
    # For small instances, solve exactly via permutation enumeration
    # For larger instances, we'd use PuLP with MTZ formulation
    
    if n <= 12:
        # Exact enumeration: fix city 0 as start, permute the rest
        best_cost = float('inf')
        best_route = None
        other_cities = list(range(1, n))
        
        for perm in permutations(other_cities):
            route = [0] + list(perm)
            cost = 0
            for i in range(n):
                cost += dist[route[i]][route[(i + 1) % n]]
            if cost < best_cost:
                best_cost = cost
                best_route = route
        
        print(f"Optimal route: {[cities[i] for i in best_route]}")
        print(f"OBJECTIVE_VALUE: {best_cost}")
    else:
        # Use PuLP with MTZ subtour elimination
        import gurobi_pulp_compat as pulp
        
        prob = pulp.LpProblem("TSP", pulp.LpMinimize)
        
        # Decision variables
        x = {}
        for i in range(n):
            for j in range(n):
                if i != j:
                    x[i, j] = pulp.LpVariable(f"x_{i}_{j}", cat='Binary')
        
        # MTZ variables
        u = {}
        for i in range(1, n):
            u[i] = pulp.LpVariable(f"u_{i}", lowBound=1, upBound=n - 1, cat='Continuous')
        
        # Objective
        prob += pulp.lpSum(dist[i][j] * x[i, j] for i in range(n) for j in range(n) if i != j)
        
        # Each city is left exactly once
        for i in range(n):
            prob += pulp.lpSum(x[i, j] for j in range(n) if j != i) == 1
        
        # Each city is entered exactly once
        for j in range(n):
            prob += pulp.lpSum(x[i, j] for i in range(n) if i != j) == 1
        
        # MTZ subtour elimination
        for i in range(1, n):
            for j in range(1, n):
                if i != j:
                    prob += u[i] - u[j] + n * x[i, j] <= n - 1
        
        prob.solve(pulp.GUROBI_CMD(msg=0))
        
        obj_val = pulp.value(prob.objective)
        print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    solve_tsp()