import os
import csv

def load_data():
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    data = {}
    filepath = os.path.join(base_dir, 'table_1_7.csv')
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            data.setdefault('table', []).append(row)
    return data