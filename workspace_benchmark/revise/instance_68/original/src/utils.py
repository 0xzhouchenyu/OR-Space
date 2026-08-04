import csv
import os

def load_distances(data_dir):
    """Load distance data from table_1.csv"""
    filepath = os.path.join(data_dir, 'table_1.csv')
    distances = {}
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            yard = row['Coal_Yard'].strip()
            area = int(row['Residential_Area'].strip())
            dist = float(row['Distance_km'].strip())
            distances[(yard, area)] = dist
    return distances

def load_parameters(data_dir):
    """Load general parameters from general_parameters.csv"""
    filepath = os.path.join(data_dir, 'general_parameters.csv')
    params = {}
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['Parameter_Name'].strip()
            value = float(row['Value'].strip())
            params[name] = value
    return params