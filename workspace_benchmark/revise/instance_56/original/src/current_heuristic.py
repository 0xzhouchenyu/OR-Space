import os
import csv
from gurobi_pulp_compat import *

# Load data
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# Load monthly prices
months = []
purchase_prices = {}
selling_prices = {}
with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        m = int(row['Month'])
        months.append(m)
        purchase_prices[m] = float(row['Purchase_Price_yuan_per_dan'])
        selling_prices[m] = float(row['Selling_Price_yuan_per_dan'])

# Load general parameters
params = {}
with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        params[row['Parameter_Name']] = float(row['Value'])

warehouse_capacity = params['warehouse_capacity']
initial_stock = params['initial_stock']
initial_funds = params['initial_funds']
end_inventory = params['end_of_quarter_inventory']

# Create LP model
model = LpProblem("Grain_Trading", LpMaximize)

buy = {m: LpVariable(f"buy_{m}", lowBound=0) for m in months}
sell = {m: LpVariable(f"sell_{m}", lowBound=0) for m in months}
stock = {m: LpVariable(f"stock_{m}", lowBound=0) for m in months}
funds = {m: LpVariable(f"funds_{m}", lowBound=0) for m in months}

# Objective: maximize final funds - initial funds (profit)
model += funds[months[-1]] - initial_funds, "Total_Profit"

# Constraints for each month
for m in months:
    prev_stock = initial_stock if m == 1 else stock[m - 1]
    prev_funds = initial_funds if m == 1 else funds[m - 1]

    # Stock balance
    model += stock[m] == prev_stock - sell[m] + buy[m], f"stock_balance_{m}"

    # Funds balance
    model += funds[m] == prev_funds + sell[m] * selling_prices[m] - buy[m] * purchase_prices[m], f"funds_balance_{m}"

    # Warehouse capacity
    model += stock[m] <= warehouse_capacity, f"warehouse_{m}"

    # Can only sell what was in stock before this month's purchase
    model += sell[m] <= prev_stock, f"sell_limit_{m}"

# End of quarter inventory requirement
model += stock[months[-1]] >= end_inventory, f"end_inventory"

# Solve
model.solve(GUROBI_CMD(msg=0))

profit = value(model.objective)
print(f"Status: {LpStatus[model.status]}")
for m in months:
    print(f"Month {m}: Buy={value(buy[m]):.1f}, Sell={value(sell[m]):.1f}, Stock={value(stock[m]):.1f}, Funds={value(funds[m]):.1f}")

print(f"OBJECTIVE_VALUE: {profit}")