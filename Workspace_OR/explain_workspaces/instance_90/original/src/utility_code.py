import csv
import os

def load_general_parameters(filepath):
    """Load general parameters from CSV file and return as a dictionary."""
    params = {}
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['Parameter_Name'].strip()
            value = float(row['Value'].strip())
            params[name] = value
    return params