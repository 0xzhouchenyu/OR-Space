import csv
import os

def load_goods_data(filepath):
    goods = {}
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            goods[row['Goods_Type'].strip()] = {
                'quantity': int(row['Quantity'].strip()),
                'weight': float(row['Weight_per_Unit'].strip())
            }
    return goods

def load_parameters(filepath):
    params = {}
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name'].strip()] = float(row['Value'].strip())
    return params