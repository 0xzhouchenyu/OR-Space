import os
import csv

def load_coverage_data(data_dir):
    """Load the coverage data from table_1.csv.
    
    Returns:
        areas: list of all area codes
        coverage: dict mapping each area to the set of areas it can cover
    """
    filepath = os.path.join(data_dir, 'table_1.csv')
    coverage = {}
    areas = []
    
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)  # skip header
        for row in reader:
            if not row or not row[0].strip():
                continue
            area_code = row[0].strip()
            areas.append(area_code)
            # The covered areas are in the second column onwards, but they might be split across columns
            # because the CSV has commas within the coverage list
            covered_raw = ','.join(row[1:])
            covered_areas = [x.strip() for x in covered_raw.split(',') if x.strip()]
            coverage[area_code] = set(covered_areas)
    
    return areas, coverage


def load_general_parameters(data_dir):
    """Load general parameters from general_parameters.csv."""
    filepath = os.path.join(data_dir, 'general_parameters.csv')
    params = {}
    
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name'].strip()] = row['Value'].strip()
    
    return params