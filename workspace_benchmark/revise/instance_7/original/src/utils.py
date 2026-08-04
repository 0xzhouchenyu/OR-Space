import csv
import os


def load_csv_data(filepath):
    """Load CSV file and return list of dictionaries."""
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data