from gurobi_execution_record import install_gurobi_objective_recorder
install_gurobi_objective_recorder('Advanced_38')
import os
import sys
from itertools import permutations
from utils import load_processing_times, compute_makespan

def main():
    # Load data
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    processing_times = load_processing_times(os.path.join(data_dir, 'table_1.csv'))
    
    n_products = len(processing_times)
    n_machines = len(processing_times[0])
    
    print(f"Number of products: {n_products}")
    print(f"Number of machines: {n_machines}")
    print(f"Processing times: {processing_times}")
    
    # Enumerate all permutations to find optimal sequence
    best_makespan = float('inf')
    best_sequence = None
    
    for perm in permutations(range(n_products)):
        makespan = compute_makespan(list(perm), processing_times, n_machines)
        print(f"Sequence {[p+1 for p in perm]}: makespan = {makespan}")
        if makespan < best_makespan:
            best_makespan = makespan
            best_sequence = perm
    
    print(f"\nOptimal sequence: {[p+1 for p in best_sequence]}")
    print(f"Optimal makespan: {best_makespan}")
    
    print(f"OBJECTIVE_VALUE: {best_makespan}")

if __name__ == "__main__":
    main()