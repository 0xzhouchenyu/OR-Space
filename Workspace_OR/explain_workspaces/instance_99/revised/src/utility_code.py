import csv
import os


def load_csv(filename):
    """Load a CSV file and return headers and rows."""
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', filename)
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows


def load_general_parameters(filename='general_parameters.csv'):
    """Load general parameters into a dictionary."""
    rows = load_csv(filename)
    params = {}
    for row in rows:
        params[row['Parameter_Name']] = float(row['Value'])
    return params


def load_reliability_table(filename='table_1.csv'):
    """Load reliability table. Returns dict: {num_spares: [r1, r2, r3]}"""
    rows = load_csv(filename)
    reliability = {}
    for row in rows:
        n_spares = int(row['Number_of_Spares'])
        r1 = float(row['Component_1_Reliability'])
        r2 = float(row['Component_2_Reliability'])
        r3 = float(row['Component_3_Reliability'])
        reliability[n_spares] = [r1, r2, r3]
    return reliability
