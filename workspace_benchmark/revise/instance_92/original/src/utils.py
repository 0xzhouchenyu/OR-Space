import csv

def load_parameters(filepath):
    """Load general parameters from CSV into a dictionary."""
    params = {}
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name'].strip()] = row['Value'].strip()
    return params