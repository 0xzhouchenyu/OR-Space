import csv

def load_parameters(filepath):
    """Load general parameters from CSV file and return as a dictionary."""
    params = {}
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['Parameter_Name'].strip()
            value_str = row['Value'].strip()
            
            # Handle ratio values like "5:2"
            if ':' in value_str:
                params[name + '_raw'] = value_str
                parts = value_str.split(':')
                params[name] = (int(parts[0]), int(parts[1]))
            else:
                try:
                    value = int(value_str)
                except ValueError:
                    try:
                        value = float(value_str)
                    except ValueError:
                        value = value_str
                params[name] = value
    return params