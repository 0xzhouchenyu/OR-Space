# Utility functions (minimal for this problem)
def read_csv(filepath):
    import csv
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        return list(reader)