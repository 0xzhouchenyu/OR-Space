import csv


def load_general_parameters(filepath):
    """Load general parameters from CSV file into a dictionary."""
    params = {}
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['Parameter_Name'].strip()
            value_str = row['Value'].strip()
            # Try to convert to numeric
            try:
                value = int(value_str)
            except ValueError:
                try:
                    value = float(value_str)
                except ValueError:
                    value = value_str
            params[name] = value
    return params
