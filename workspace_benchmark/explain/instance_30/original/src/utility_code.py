import csv


def load_feed_data(filepath):
    feeds = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            feed = {
                'Feed': int(row['Feed']),
                'Protein_g': float(row['Protein_g']),
                'Minerals_g': float(row['Minerals_g']),
                'Vitamins_mg': float(row['Vitamins_mg']),
                'Price_Y_per_kg': float(row['Price_Y_per_kg']),
            }
            feeds.append(feed)
    return feeds


def load_general_parameters(filepath):
    params = {}
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name']] = float(row['Value'])
    return params