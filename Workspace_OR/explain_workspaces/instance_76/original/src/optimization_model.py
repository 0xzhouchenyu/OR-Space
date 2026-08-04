import os
import csv
from gurobi_pulp_compat import *

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, '..', 'data')
    
    # Read table_1.csv
    quarters = []
    purchase_price = {}
    sale_price = {}
    max_sales = {}
    
    with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            q = row['Quarter'].strip()
            quarters.append(q)
            purchase_price[q] = float(row['Purchase_Price_10k_yuan_per_10k_m2'].strip())
            sale_price[q] = float(row['Sale_Price_10k_yuan_per_10k_m2'].strip())
            max_sales[q] = float(row['Estimated_Max_Sales_Volume_10k_m3'].strip())
    
    # Read general_parameters.csv
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        params = {}
        for row in reader:
            params[row['Parameter_Name'].strip()] = row['Value'].strip()
    
    max_storage = float(params['max_storage_capacity'])  # 200,000 m³ = 20 units of 10,000 m³
    storage_cost_a = float(params['storage_cost_a'])      # 70 yuan/m³
    storage_cost_b = float(params['storage_cost_b'])      # 100 yuan/m³/quarter
    
    # Convert storage capacity to units of 10,000 m³
    max_storage_wm3 = max_storage / 10000.0  # 20 units of 10,000 m³
    
    # Convert storage costs to 10,000 yuan per 10,000 m³
    # 70 yuan/m³ = 70 units of 10,000 yuan per 10,000 m³
    # 100 yuan/m³/quarter = 100 units of 10,000 yuan per 10,000 m³ per quarter
    storage_cost_a_w = storage_cost_a * 10000.0 / 10000.0
    storage_cost_b_w = storage_cost_b * 10000.0 / 10000.0
    
    # Storage cost for u quarters, in 10,000 yuan per 10,000 m³
    
    # Quarter indices: 0=Winter, 1=Spring, 2=Summer, 3=Autumn
    n = len(quarters)
    
    # Decision variables:
    # x[i][j] = amount purchased in quarter i and sold in quarter j (10,000 m³)
    # where j >= i and j <= 3 (must sell by autumn)
    
    prob = LpProblem("Timber_Profit_Maximization", LpMaximize)
    
    x = {}
    for i in range(n):
        for j in range(i, n):
            x[i, j] = LpVariable(f"x_{i}_{j}", lowBound=0)
    
    # Objective: maximize profit
    # For x[i,j]: revenue = sale_price[j] * x[i,j]
    #             cost = purchase_price[i] * x[i,j]
    #             storage cost = (storage_cost_a_w + storage_cost_b_w * (j-i)) * x[i,j] if j > i, else 0
    profit_terms = []
    for i in range(n):
        for j in range(i, n):
            u = j - i  # quarters stored
            revenue = sale_price[quarters[j]]
            cost = purchase_price[quarters[i]]
            if u > 0:
                s_cost = storage_cost_a_w + storage_cost_b_w * u
            else:
                s_cost = 0
            profit_terms.append((revenue - cost - s_cost) * x[i, j])
    
    prob += lpSum(profit_terms)
    
    # Sales constraints: total sold in quarter j <= max_sales[j]
    for j in range(n):
        prob += lpSum(x[i, j] for i in range(j + 1)) <= max_sales[quarters[j]]
    
    # Storage constraints: at end of each quarter, stored timber <= max_storage
    for t in range(n - 1):
        # After quarter t, stored = sum of x[i,j] where i <= t and j > t
        stored = lpSum(x[i, j] for i in range(t + 1) for j in range(t + 1, n))
        prob += stored <= max_storage_wm3
    
    prob.solve(GUROBI_CMD(msg=0))
    
    obj_val = value(prob.objective)
    
    for i in range(n):
        for j in range(i, n):
            val = value(x[i, j])
            if val and val > 0.001:
                u = j - i
                print(f"Buy in {quarters[i]}, sell in {quarters[j]} (store {u}q): {val:.2f} x 10,000 m³")
    
    print(f"OBJECTIVE_VALUE: {obj_val:.1f}")

if __name__ == "__main__":
    main()
