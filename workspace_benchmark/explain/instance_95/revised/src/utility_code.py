import csv
import os

def load_table_1(data_dir):
    """Load the weekly demand, capacity, and cost data."""
    filepath = os.path.join(data_dir, 'table_1.csv')
    weeks = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Week'].strip().lower() == 'total':
                continue
            weeks.append({
                'week': int(row['Week']),
                'demand': float(row['Demand_1000_boxes']),
                'capacity': float(row['Production_Capacity_1000_boxes']),
                'cost': float(row['Cost_per_1000_boxes_1000_yuan'])
            })
    return weeks

def load_general_parameters(data_dir):
    """Load general parameters."""
    filepath = os.path.join(data_dir, 'general_parameters.csv')
    params = {}
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name'].strip()] = float(row['Value'])
    return params