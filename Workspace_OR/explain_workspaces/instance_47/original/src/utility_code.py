import csv
import os

def load_csv(filename):
    """Load a CSV file and return headers and rows."""
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', filename)
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        headers = next(reader)
        rows = []
        for row in reader:
            rows.append(row)
    return headers, rows

def load_general_parameters(filename='general_parameters.csv'):
    """Load general parameters into a dictionary."""
    headers, rows = load_csv(filename)
    params = {}
    for row in rows:
        name = row[0].strip()
        try:
            value = float(row[1].strip())
        except ValueError:
            value = row[1].strip()
        params[name] = value
    return params

def load_crop_data(filename='table_1.csv'):
    """Load crop data from table_1.csv."""
    headers, rows = load_csv(filename)
    # headers: Item, Soybean, Corn, Wheat
    crops = [h.strip() for h in headers[1:]]
    data = {}
    for row in rows:
        item = row[0].strip()
        values = [float(v.strip()) for v in row[1:]]
        data[item] = dict(zip(crops, values))
    return crops, data