from gurobi_execution_record import install_gurobi_objective_recorder
install_gurobi_objective_recorder('Advanced_35')
import os
import sys
import csv
from itertools import permutations

def load_data():
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    filepath = os.path.join(base_dir, 'table_1.csv')
    
    batches = []
    processing_times = []
    
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        num_vats = len(header) - 1  # exclude Batch column
        
        for row in reader:
            batch_id = int(row[0])
            times = [float(row[j+1]) for j in range(num_vats)]
            batches.append(batch_id)
            processing_times.append(times)
    
    return batches, processing_times, num_vats

def compute_makespan(perm, processing_times, num_vats):
    """Compute makespan for a given permutation of jobs."""
    n = len(perm)
    # completion[i][j] = completion time of i-th job in permutation on machine j
    completion = [[0.0] * num_vats for _ in range(n)]
    
    for i in range(n):
        job = perm[i]
        for j in range(num_vats):
            # Start time is max of:
            # - completion of this job on previous machine (if j > 0)
            # - completion of previous job on this machine (if i > 0)
            start = 0.0
            if i > 0:
                start = max(start, completion[i-1][j])
            if j > 0:
                start = max(start, completion[i][j-1])
            completion[i][j] = start + processing_times[job][j]
    
    return completion[n-1][num_vats-1]

def solve():
    batches, processing_times, num_vats = load_data()
    n = len(batches)
    
    # Job indices are 0-based
    job_indices = list(range(n))
    
    best_makespan = float('inf')
    best_perm = None
    
    # Enumerate all permutations (5! = 120, very manageable)
    for perm in permutations(job_indices):
        ms = compute_makespan(perm, processing_times, num_vats)
        if ms < best_makespan:
            best_makespan = ms
            best_perm = perm
    
    # Print solution details
    print(f"Number of batches: {n}")
    print(f"Number of vats: {num_vats}")
    print(f"Best permutation (batch order): {[batches[i] for i in best_perm]}")
    
    # Print schedule details
    completion = [[0.0] * num_vats for _ in range(n)]
    for i in range(n):
        job = best_perm[i]
        for j in range(num_vats):
            start = 0.0
            if i > 0:
                start = max(start, completion[i-1][j])
            if j > 0:
                start = max(start, completion[i][j-1])
            completion[i][j] = start + processing_times[job][j]
        print(f"Batch {batches[job]}: completion times = {completion[i]}")
    
    print(f"Optimal makespan: {best_makespan}")
    print(f"OBJECTIVE_VALUE: {best_makespan}")

if __name__ == '__main__':
    solve()