import csv
import os


def load_processing_times(filepath):
    """Load processing times from CSV file.
    Returns a list of lists: processing_times[i][j] = time for product i on machine j.
    """
    processing_times = []
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)  # Skip header
        for row in reader:
            # First column is product name, rest are processing times
            times = [int(val) for val in row[1:]]
            processing_times.append(times)
    return processing_times


def compute_makespan(sequence, processing_times, n_machines):
    """Compute the makespan for a given job sequence in a flow shop.
    
    sequence: list of job indices (0-based)
    processing_times: processing_times[job][machine]
    n_machines: number of machines
    """
    n_jobs = len(sequence)
    # completion[i][j] = completion time of i-th job in sequence on machine j
    completion = [[0] * n_machines for _ in range(n_jobs)]
    
    for i in range(n_jobs):
        job = sequence[i]
        for j in range(n_machines):
            start_time = 0
            if i > 0:
                start_time = max(start_time, completion[i-1][j])  # previous job on same machine
            if j > 0:
                start_time = max(start_time, completion[i][j-1])  # same job on previous machine
            completion[i][j] = start_time + processing_times[job][j]
    
    return completion[n_jobs - 1][n_machines - 1]