from gurobi_execution_record import install_gurobi_objective_recorder
install_gurobi_objective_recorder('Advanced_82')
import os
import csv
from itertools import product

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, '..', 'data')
    
    # Read general parameters
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        params = {}
        for row in reader:
            params[row['Parameter_Name'].strip()] = float(row['Value'].strip())
    
    total_space = params['mall_total_space']
    rent_pct = params['rent_percentage'] / 100.0
    
    # Read store data
    stores = []
    with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            area = int(row['Area_per_Shop_m2'].strip())
            min_n = int(row['Min'].strip())
            max_n = int(row['Max'].strip())
            profits = {}
            for k in range(1, 4):
                key = f'Profit_{k}_Store' if k == 1 else f'Profit_{k}_Stores'
                val = row.get(key, '-').strip()
                if val and val != '-':
                    profits[k] = float(val)
            stores.append({
                'name': row['Store_Type'].strip(),
                'area': area,
                'min': min_n,
                'max': max_n,
                'profits': profits  # per-store profit when n stores of this type
            })
    
    # Enumerate all combinations
    ranges = []
    for s in stores:
        ranges.append(range(s['min'], s['max'] + 1))
    
    best_profit = -1
    best_combo = None
    
    for combo in product(*ranges):
        # Check space constraint
        total_area = sum(combo[i] * stores[i]['area'] for i in range(len(stores)))
        if total_area > total_space:
            continue
        
        # Calculate total profit
        total_profit = 0
        valid = True
        for i, n in enumerate(combo):
            if n == 0:
                continue
            if n in stores[i]['profits']:
                # Per-store profit × number of stores
                total_profit += n * stores[i]['profits'][n]
            else:
                valid = False
                break
        
        if valid and total_profit > best_profit:
            best_profit = total_profit
            best_combo = combo
    
    total_rent = rent_pct * best_profit
    
    print(f"Best combination: {best_combo}")
    for i, s in enumerate(stores):
        print(f"  {s['name']}: {best_combo[i]} stores")
    print(f"Total area used: {sum(best_combo[i] * stores[i]['area'] for i in range(len(stores)))}")
    print(f"Total profit: {best_profit}")
    print(f"Total rent (objective): {total_rent}")
    print(f"OBJECTIVE_VALUE: {total_rent}")

if __name__ == '__main__':
    main()