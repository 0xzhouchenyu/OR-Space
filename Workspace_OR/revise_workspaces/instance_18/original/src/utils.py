# Utility functions for the textile factory optimization problem
import csv
import os

def load_parameters(data_dir):
    """Load general parameters from CSV file."""
    params = {}
    filepath = os.path.join(data_dir, 'general_parameters.csv')
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name'].strip()] = float(row['Value'].strip())
    return params