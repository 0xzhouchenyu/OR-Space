import csv
import os


def load_restaurant_data(filepath):
    """Load restaurant data from CSV file."""
    restaurants = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            restaurants.append({
                'name': row['Restaurant'].strip(),
                'revenue': float(row['Annual_Revenue'].strip()),
                'cost': float(row['Cost'].strip())
            })
    return restaurants


def load_general_parameters(filepath):
    """Load general parameters from CSV file."""
    params = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            param_name = row['Parameter_Name'].strip()
            value = float(row['Value'].strip())
            params[param_name] = value
    return params