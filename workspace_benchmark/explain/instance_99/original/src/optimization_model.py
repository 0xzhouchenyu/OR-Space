from gurobi_execution_record import install_gurobi_objective_recorder
install_gurobi_objective_recorder('Advanced_99')
import os
import sys
from itertools import product

# Add parent directory to path if needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import load_general_parameters, load_reliability_table

def solve():
    # Load data
    params = load_general_parameters()
    reliability = load_reliability_table()
    
    # Extract parameters
    unit_price = [
        params['unit_price_component_1'],
        params['unit_price_component_2'],
        params['unit_price_component_3']
    ]
    unit_weight = [
        params['unit_weight_component_1'],
        params['unit_weight_component_2'],
        params['unit_weight_component_3']
    ]
    total_budget = params['total_budget']
    weight_limit = params['weight_limit']
    
    # Get max number of spares
    max_spares = max(reliability.keys())
    
    # Enumerate all combinations of spares for 3 components
    best_reliability = 0.0
    best_combo = None
    
    for s1, s2, s3 in product(range(max_spares + 1), repeat=3):
        # Cost constraint: spare parts cost (not including the base component)
        # The number of spares is the extra parts, so cost = s1*p1 + s2*p2 + s3*p3
        cost = s1 * unit_price[0] + s2 * unit_price[1] + s3 * unit_price[2]
        weight = s1 * unit_weight[0] + s2 * unit_weight[1] + s3 * unit_weight[2]
        
        if cost > total_budget:
            continue
        if weight > weight_limit:
            continue
        
        # Check if all spare counts are in the reliability table
        if s1 not in reliability or s2 not in reliability or s3 not in reliability:
            continue
        
        r1 = reliability[s1][0]
        r2 = reliability[s2][1]
        r3 = reliability[s3][2]
        
        system_reliability = r1 * r2 * r3
        
        if system_reliability > best_reliability:
            best_reliability = system_reliability
            best_combo = (s1, s2, s3)
    
    print(f"Optimal spare parts allocation: Component 1: {best_combo[0]}, Component 2: {best_combo[1]}, Component 3: {best_combo[2]}")
    print(f"Total cost: {best_combo[0]*unit_price[0] + best_combo[1]*unit_price[1] + best_combo[2]*unit_price[2]}")
    print(f"Total weight: {best_combo[0]*unit_weight[0] + best_combo[1]*unit_weight[1] + best_combo[2]*unit_weight[2]}")
    
    r1 = reliability[best_combo[0]][0]
    r2 = reliability[best_combo[1]][1]
    r3 = reliability[best_combo[2]][2]
    print(f"Component reliabilities: {r1}, {r2}, {r3}")
    print(f"OBJECTIVE_VALUE: {best_reliability}")

if __name__ == '__main__':
    solve()