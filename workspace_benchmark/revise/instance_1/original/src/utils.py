import csv
import os

def load_csv(filename):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(base_dir, '..', 'data', filename)
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            rows.append(row)
    return rows

def load_parameters():
    rows = load_csv('general_parameters.csv')
    params = {}
    for row in rows:
        name = row['Parameter_Name'].strip()
        val = row['Value'].strip()
        try:
            if '.' in val:
                params[name] = float(val)
            else:
                params[name] = int(val)
        except ValueError:
            params[name] = val
    return params

def load_demand():
    rows = load_csv('table_1.csv')
    demand = {}
    for row in rows:
        week = int(row['Week'].strip())
        demand[week] = {
            'I': int(row['I'].strip()),
            'II': int(row['II'].strip())
        }
    return demand