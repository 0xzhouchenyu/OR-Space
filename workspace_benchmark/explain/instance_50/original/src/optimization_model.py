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
    
    # Objective: maximize total profit (revenue - cost)
    prob += lpSum(sell_price[m] * sell[m] - buy_price[m] * buy[m] for m in months)
    
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
    
    # Solve
    prob.solve(GUROBI_CMD(msg=0))
    
    # Print solution details
    for m in months:
        print(f"Month {m}: Buy={value(buy[m]):.1f} @ {buy_price[m]}, "
              f"Sell={value(sell[m]):.1f} @ {sell_price[m]}, "
              f"Stock={value(stock[m]):.1f}")
    
    obj_val = value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()