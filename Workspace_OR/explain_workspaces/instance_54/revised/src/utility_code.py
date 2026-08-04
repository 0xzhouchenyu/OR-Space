import csv
import os

def load_table_1(data_dir):
    """Load and parse table_1.csv to extract equipment hours, processing times, and base profit values."""
    filepath = os.path.join(data_dir, 'table_1.csv')

    equipment_names = []
    products = []
    processing_times = {}  # (equipment, product) -> time
    effective_hours = {}   # equipment -> hours
    profit = {}            # product -> base economic value

    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        # header: Equipment_Code, I, II, III, Effective_Monthly_Equipment_Hours
        products = header[1:-1]  # ['I', 'II', 'III']

        for row in reader:
            if not row or all(col == '' for col in row):
                continue
            if row[0].startswith('Unit_Product_Profit'):
                # This is the base profit row
                for j, prod in enumerate(products):
                    if row[j + 1] != '':
                        profit[prod] = float(row[j + 1])
            else:
                equip = row[0]
                if equip == '':
                    continue
                equipment_names.append(equip)
                effective_hours[equip] = float(row[-1])
                for j, prod in enumerate(products):
                    processing_times[(equip, prod)] = float(row[j + 1])

    return products, equipment_names, processing_times, effective_hours, profit


def load_general_parameters(data_dir):
    """Load general_parameters.csv into a dictionary: name -> value (as string)."""
    filepath = os.path.join(data_dir, 'general_parameters.csv')
    params = {}
    if not os.path.exists(filepath):
        return params

    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('Parameter_Name', '').strip()
            value = row.get('Value', '').strip()
            if name:
                params[name] = value
    return params
