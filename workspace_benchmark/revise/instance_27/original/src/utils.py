import os
import csv

def load_table1(data_dir):
    filepath = os.path.join(data_dir, 'table_1.csv')
    equipment = []
    proc_times = {}
    eff_hours = {}
    op_costs = {}
    
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            e = row['Equipment'].strip()
            equipment.append(e)
            proc_times[e] = {}
            for p in ['Product_I', 'Product_II', 'Product_III']:
                val = row[p].strip() if row[p].strip() else None
                proc_times[e][p] = float(val) if val else None
            eff_hours[e] = float(row['Effective_Machine_Hours'].strip())
            op_costs[e] = float(row['Operating_Costs_Full_Capacity_Yuan'].strip())
    
    return equipment, proc_times, eff_hours, op_costs

def load_general_params(data_dir):
    filepath = os.path.join(data_dir, 'general_parameters.csv')
    raw_costs = {}
    prices = {}
    
    mapping_raw = {
        'raw_material_cost_product_I': 'Product_I',
        'raw_material_cost_product_II': 'Product_II',
        'raw_material_cost_product_III': 'Product_III',
    }
    mapping_price = {
        'unit_price_product_I': 'Product_I',
        'unit_price_product_II': 'Product_II',
        'unit_price_product_III': 'Product_III',
    }
    
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['Parameter_Name'].strip()
            val = float(row['Value'].strip())
            if name in mapping_raw:
                raw_costs[mapping_raw[name]] = val
            if name in mapping_price:
                prices[mapping_price[name]] = val
    
    return raw_costs, prices