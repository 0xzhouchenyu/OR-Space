import csv
import os

def load_csv(filename):
    """Load a CSV file and return a list of dictionaries."""
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', filename)
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        return list(reader)

def load_general_parameters(filename='general_parameters.csv'):
    """Load general parameters into a dictionary."""
    rows = load_csv(filename)
    params = {}
    for row in rows:
        name = row['Parameter_Name']
        value = row['Value']
        # Try to convert to numeric
        try:
            if '.' in value:
                params[name] = float(value)
            else:
                params[name] = int(value)
        except ValueError:
            params[name] = value
    return params

def load_task_methods(filename='table_1.csv'):
    """Load task-method data."""
    rows = load_csv(filename)
    data = []
    for row in rows:
        data.append({
            'Task': row['Task'],
            'Method': row['Method'],
            'Effective_Hours': float(row['Effective_Hours']),
            'Fixed_Cost': float(row['Fixed_Cost'])
        })
    return data