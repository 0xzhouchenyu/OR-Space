import csv
import os

def load_csv(filename):
    """Load a CSV file and return list of dictionaries."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(base_dir, '..', 'data', filename)
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        return [row for row in reader]

def load_demand():
    """Load demand data from table_1.csv."""
    rows = load_csv('table_1.csv')
    demand = {}
    for row in rows:
        month = row['Month']
        product = row['Product']
        units = int(row['Market_Demand_Units'])
        demand[(month, product)] = units
    return demand

def load_parameters():
    """Load general parameters."""
    rows = load_csv('general_parameters.csv')
    params = {}
    for row in rows:
        name = row['Parameter_Name']
        value = float(row['Value'])
        params[name] = value
    return params