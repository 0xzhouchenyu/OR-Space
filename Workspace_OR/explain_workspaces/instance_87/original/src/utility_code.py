import csv

def load_parameters(filepath):
    """Load parameters from a CSV file into a dictionary."""
    params = {}
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['Parameter_Name'].strip()
            value = float(row['Value'].strip())
            params[name] = value
    return params