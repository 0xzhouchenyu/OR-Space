import csv
import os

def load_car_data(data_dir):
    filepath = os.path.join(data_dir, 'table_1.csv')
    cars = {}
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            i = int(row['i'])
            length = float(row['lambda_i'])
            cars[i] = length
    return cars

def load_parameters(data_dir):
    filepath = os.path.join(data_dir, 'general_parameters.csv')
    params = {}
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['Parameter_Name'].strip()
            value = float(row['Value'])
            params[name] = value
    return params