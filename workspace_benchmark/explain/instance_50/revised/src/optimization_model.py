import os
import csv
from gurobi_pulp_compat import *

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, '..', 'data')
    
    # Load general parameters
    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name']] = float(row['Value'])
    
    warehouse_capacity = int(params['warehouse_capacity'])
    initial_stock = int(params['initial_stock'])
    fixed_order_cost = float(params['fixed_order_cost'])
    august_bulk_threshold = float(params['august_bulk_order_threshold'])
    august_bulk_fee = float(params['august_bulk_receiving_fee'])
    
    # Load monthly data
    months = []
    buy_price = {}
    sell_price = {}
    with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            m = int(row['Month'])
            months.append(m)
            buy_price[m] = float(row['Buy'])
            sell_price[m] = float(row['Sell'])
    
    # Create LP problem
    prob = LpProblem("MaxRevenue", LpMaximize)
    
    # Decision variables
    buy = {m: LpVariable(f"buy_{m}", lowBound=0) for m in months}
    sell = {m: LpVariable(f"sell_{m}", lowBound=0) for m in months}
    stock = {m: LpVariable(f"stock_{m}", lowBound=0, upBound=warehouse_capacity) for m in months}
    buy_bin = {m: LpVariable(f"buy_bin_{m}", cat='Binary') for m in months}
    august_bulk = LpVariable("august_bulk_receiving", cat='Binary')
    
    # Objective: maximize total profit (revenue - cost - fixed_order_cost)
    prob += lpSum(sell_price[m] * sell[m] - buy_price[m] * buy[m] - fixed_order_cost * buy_bin[m] for m in months) - august_bulk_fee * august_bulk
    
    # Stock balance constraints
    for i, m in enumerate(months):
        if i == 0:
            prev_stock = initial_stock
        else:
            prev_stock = stock[months[i-1]]
        
        # Stock balance: stock[m] = prev_stock + buy[m] - sell[m]
        prob += stock[m] == prev_stock + buy[m] - sell[m], f"balance_{m}"
        
        # After buying, before selling, warehouse constraint:
        # prev_stock + buy[m] <= warehouse_capacity
        prob += prev_stock + buy[m] <= warehouse_capacity, f"warehouse_after_buy_{m}"
        
        # Fixed cost constraint
        prob += buy[m] <= warehouse_capacity * buy_bin[m], f"fixed_cost_{m}"
        if m == 8:
            prob += buy[m] <= august_bulk_threshold + warehouse_capacity * august_bulk, "august_bulk_receiving"
    
    # Solve
    prob.solve(GUROBI_CMD(msg=0))
    
    obj_val = value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()
