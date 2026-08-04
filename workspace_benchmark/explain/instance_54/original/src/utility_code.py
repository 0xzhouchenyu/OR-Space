import csv
import os

def load_table_1(data_dir):
    """Load and parse table_1.csv to extract equipment hours, processing times, and profits."""
    filepath = os.path.join(data_dir, 'table_1.csv')
    
    equipment_names = []
    products = []
    processing_times = {}  # (equipment, product) -> time
    effective_hours = {}   # equipment -> hours
    profit = {}            # product -> profit
    
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        # header: Equipment_Code, I, II, III, Effective_Monthly_Equipment_Hours
        products = header[1:-1]  # ['I', 'II', 'III']
        
        for row in reader:
            if row[0].startswith('Unit_Product_Profit'):
                # This is the profit row
                for j, prod in enumerate(products):
                    profit[prod] = float(row[j + 1])
            else:
                equip = row[0]
                equipment_names.append(equip)
                effective_hours[equip] = float(row[-1])
                for j, prod in enumerate(products):
                    processing_times[(equip, prod)] = float(row[j + 1])
    
    return products, equipment_names, processing_times, effective_hours, profit