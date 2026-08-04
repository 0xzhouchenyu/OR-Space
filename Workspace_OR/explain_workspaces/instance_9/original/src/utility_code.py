import csv

def load_toy_data(filepath):
    toys = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            toys.append({
                'type': row['Toy_Type'].strip(),
                'profit': float(row['Profit_Per_Unit']),
                'wood': float(row['Wood_Required_Per_Unit']),
                'steel': float(row['Steel_Required_Per_Unit']),
            })
    return toys

def load_general_parameters(filepath):
    params = {}
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name'].strip()] = float(row['Value'])
    return params