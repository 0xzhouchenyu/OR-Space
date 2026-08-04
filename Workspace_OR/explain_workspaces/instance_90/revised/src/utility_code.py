import csv

def load_general_parameters(filepath):
    params = {}
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name'].strip()] = float(row['Value'].strip())
    return params