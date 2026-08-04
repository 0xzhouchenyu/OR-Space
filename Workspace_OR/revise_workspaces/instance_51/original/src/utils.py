import csv

def load_demand(filepath):
    """Load nurse demand per time period from CSV."""
    demand = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            demand.append(int(row['Required_Nurses']))
    return demand

def load_parameters(filepath):
    """Load general parameters from CSV."""
    params = {}
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name']] = row['Value']
    return params