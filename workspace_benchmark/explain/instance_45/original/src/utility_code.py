# Utility functions (minimal as required)
def load_csv_data(filepath):
    import csv
    data = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data