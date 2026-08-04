import csv

def load_csv_data(filepath):
    """Load CSV file and return list of dictionaries."""
    data = []
    with open(filepath, 'r', newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Strip whitespace from keys and values
            cleaned = {k.strip(): v.strip() for k, v in row.items() if k is not None}
            data.append(cleaned)
    return data