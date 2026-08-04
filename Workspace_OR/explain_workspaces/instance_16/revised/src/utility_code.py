import csv
import os

def load_monthly_data(filepath):
    """Load monthly purchasing and selling price data."""
    months = []
    purchasing_prices = {}
    selling_prices = {}
    
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            month = int(row['Month'])
            months.append(month)
            purchasing_prices[month] = float(row['Purchasing_Price_Yuan'])
            selling_prices[month] = float(row['Selling_Price_Yuan'])
    
    return months, purchasing_prices, selling_prices

def load_general_parameters(filepath):
    """Load general parameters."""
    params = {}
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name']] = float(row['Value'])
    return params