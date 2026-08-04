import os
import csv
from gurobi_pulp_compat import *

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, '..', 'data')

    quarters = []
    purchase_price = {}
    sale_price = {}
    max_sales = {}
    max_purchase = {}

    with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            q = row['Quarter'].strip()
            quarters.append(q)
            purchase_price[q] = float(row['Purchase_Price_10k_yuan_per_10k_m2'].strip())
            sale_price[q] = float(row['Sale_Price_10k_yuan_per_10k_m2'].strip())
            max_sales[q] = float(row['Estimated_Max_Sales_Volume_10k_m3'].strip())
            max_purchase[q] = float(row['max_purchase_10k_m3'].strip())

    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name'].strip()] = row['Value'].strip()

    max_storage = float(params['max_storage_capacity'])
    storage_cost_a = float(params['storage_cost_a'])
    storage_cost_b = float(params['storage_cost_b'])
    safety_inventory_level = float(params['safety_inventory_level_10k_m3'])
    terminal_inventory_value = float(params['terminal_inventory_value_per_10k_m3'])
    over_purchase_penalty_cost = float(params['over_purchase_penalty_cost_per_10k_m3'])

    max_storage_wm3 = max_storage / 10000.0
    storage_cost_a_w = storage_cost_a * 10000.0 / 10000.0
    storage_cost_b_w = storage_cost_b * 10000.0 / 10000.0

    n = len(quarters)
    autumn_idx = n - 1

    prob = LpProblem("Timber_Profit_Maximization_With_Inventory_Policy", LpMaximize)

    x = {}
    for i in range(n):
        for j in range(i, n):
            x[i, j] = LpVariable(f"x_{i}_{j}", lowBound=0)

    end_inventory = LpVariable("end_inventory_10k_m3", lowBound=0)
    over_stock = LpVariable("over_stock_10k_m3", lowBound=0)

    profit_terms = []
    for i in range(n):
        for j in range(i, n):
            u = j - i
            q_i = quarters[i]
            q_j = quarters[j]
            revenue = sale_price[q_j]
            cost = purchase_price[q_i]
            if u > 0:
                s_cost = storage_cost_a_w + storage_cost_b_w * u
            else:
                s_cost = 0.0
            profit_terms.append((revenue - cost - s_cost) * x[i, j])

    profit_terms.append((terminal_inventory_value - purchase_price[quarters[autumn_idx]]) * end_inventory)
    profit_terms.append(-over_purchase_penalty_cost * over_stock)

    prob += lpSum(profit_terms)

    for j in range(n):
        q_j = quarters[j]
        prob += lpSum(x[i, j] for i in range(j + 1)) <= max_sales[q_j], f"SalesCap_{q_j}"

    for t in range(n - 1):
        stored = lpSum(x[i, j] for i in range(t + 1) for j in range(t + 1, n))
        prob += stored <= max_storage_wm3, f"StorageCap_after_{quarters[t]}"

    for i in range(n):
        q_i = quarters[i]
        if i == autumn_idx:
            prob += lpSum(x[i, j] for j in range(i, n)) + end_inventory <= max_purchase[q_i], f"PurchaseCap_{q_i}"
        else:
            prob += lpSum(x[i, j] for j in range(i, n)) <= max_purchase[q_i], f"PurchaseCap_{q_i}"

    prob += end_inventory >= safety_inventory_level, "MinSafetyInventory"
    prob += end_inventory <= max_storage_wm3, "EndInventoryStorageCap"
    prob += over_stock >= end_inventory - safety_inventory_level, "OverStockDef"

    prob.solve(GUROBI_CMD(msg=0))

    obj_val = value(prob.objective)

    for i in range(n):
        for j in range(i, n):
            val = value(x[i, j])
            if val is not None and val > 0.001:
                u = j - i
                print(f"Buy in {quarters[i]}, sell in {quarters[j]} (store {u}q): {val:.2f} 10k m^3")

    end_inventory_val = value(end_inventory)
    over_stock_val = value(over_stock)
    print(f"End-of-autumn reserve inventory: {end_inventory_val:.2f} 10k m^3")
    print(f"Over-stock above safety level: {over_stock_val:.2f} 10k m^3")
    print(f"OBJECTIVE_VALUE: {obj_val:.1f}")

if __name__ == "__main__":
    main()
