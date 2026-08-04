import os
import sys
from gurobi_pulp_compat import *

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import load_coverage_data, load_general_parameters

def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    
    # Load data
    areas, coverage = load_coverage_data(data_dir)
    params = load_general_parameters(data_dir)
    
    print(f"Areas: {areas}")
    print(f"Distance limit: {params.get('distance_limit', 800)}m")
    print(f"Coverage:")
    for area, covered in coverage.items():
        print(f"  Store at {area} covers: {sorted(covered)}")
    
    # Set Covering Problem
    # Decision variables: x_j = 1 if we build a store in area j, 0 otherwise
    # Objective: minimize sum of x_j
    # Constraints: for each area i, at least one store in a location that covers i
    
    # All areas that need to be covered
    all_areas = set(areas)
    
    # Create the problem
    prob = LpProblem("MinChainStores", LpMinimize)
    
    # Decision variables
    x = {j: LpVariable(f"x_{j}", cat='Binary') for j in areas}
    
    # Objective: minimize total number of stores
    prob += lpSum(x[j] for j in areas), "TotalStores"
    
    # Constraints: each area must be covered by at least one store
    for i in areas:
        # Find which potential store locations cover area i
        covering_stores = [j for j in areas if i in coverage.get(j, set())]
        prob += lpSum(x[j] for j in covering_stores) >= 1, f"Cover_{i}"
    
    # Solve
    prob.solve(GUROBI_CMD(msg=1))
    
    print(f"\nStatus: {LpStatus[prob.status]}")
    print(f"Optimal number of stores: {value(prob.objective)}")
    
    # Print which areas get stores
    selected = [j for j in areas if value(x[j]) > 0.5]
    print(f"Store locations: {selected}")
    
    # Verify coverage
    covered_total = set()
    for j in selected:
        covered_total |= coverage[j]
    print(f"All areas covered: {all_areas.issubset(covered_total)}")
    print(f"Covered areas: {sorted(covered_total)}")
    
    obj_val = value(prob.objective)
    print(f"\nOBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()