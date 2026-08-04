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

buy_fast_capacity = params['buy_fast_capacity']
fast_purchase_premium_ratio = params['fast_purchase_premium_ratio']
credit_limit = params['credit_limit']
monthly_interest_rate = params['monthly_interest_rate']

min_inventory = {
    1: params['min_inventory_month_1'],
    2: params['min_inventory_month_2'],
    3: params['min_inventory_month_3']
}

# Create LP model
model = LpProblem("Grain_Trading_TwoChannel_Credit", LpMaximize)

# Decision variables
buy_regular = {m: LpVariable(f"buy_regular_{m}", lowBound=0) for m in months}
buy_fast = {m: LpVariable(f"buy_fast_{m}", lowBound=0) for m in months}
sell = {m: LpVariable(f"sell_{m}", lowBound=0) for m in months}
stock = {m: LpVariable(f"stock_{m}", lowBound=0) for m in months}
funds = {m: LpVariable(f"funds_{m}", lowBound=0) for m in months}
credit_used = {m: LpVariable(f"credit_used_{m}", lowBound=0) for m in months}

# Objective: maximize final funds minus initial funds minus total interest
interest_terms = []
for m in months:
    interest_terms.append(monthly_interest_rate * credit_used[m])

model += funds[months[-1]] - initial_funds - lpSum(interest_terms), "Total_Profit_with_Interest"

# Constraints for each month
for m in months:
    prev_stock = initial_stock if m == 1 else stock[m - 1]
    prev_funds = initial_funds if m == 1 else funds[m - 1]

    # Stock balance
    model += stock[m] == prev_stock - sell[m] + buy_regular[m] + buy_fast[m], f"stock_balance_{m}"

    # Sales limited by previous stock
    model += sell[m] <= prev_stock, f"sell_limit_{m}"

    # Warehouse capacity
    model += stock[m] <= warehouse_capacity, f"warehouse_{m}"

    # Minimum inventory requirement for each month
    model += stock[m] >= min_inventory[m], f"min_inventory_{m}"

    # Fast purchase capacity
    model += buy_fast[m] <= buy_fast_capacity, f"fast_capacity_{m}"

    # Credit limit
    model += credit_used[m] <= credit_limit, f"credit_limit_{m}"

    # Funds and credit balance
    regular_cost = buy_regular[m] * purchase_prices[m]
    fast_cost = buy_fast[m] * purchase_prices[m] * (1.0 + fast_purchase_premium_ratio)
    revenue = sell[m] * selling_prices[m]
    interest_cost = monthly_interest_rate * credit_used[m]

    # funds_m + credit_used_m = prev_funds + revenue - regular_cost - fast_cost - interest_cost
    model += (
        funds[m] + credit_used[m]
        == prev_funds + revenue - regular_cost - fast_cost - interest_cost
    ), f"funds_balance_{m}"

# End of quarter inventory requirement (in addition to min_inventory_3)
model += stock[months[-1]] >= end_inventory, "end_inventory"

# Solve
model.solve(GUROBI_CMD(msg=0))

status_str = LpStatus[model.status]
profit = value(model.objective)

print(f"Status: {status_str}")
for m in months:
    br = value(buy_regular[m])
    bf = value(buy_fast[m])
    s = value(sell[m])
    st = value(stock[m])
    f = value(funds[m])
    c = value(credit_used[m])
    print(
        f"Month {m}: Buy_regular={br:.1f}, Buy_fast={bf:.1f}, Sell={s:.1f}, "
        f"Stock={st:.1f}, Funds={f:.1f}, Credit_used={c:.1f}"
    )

print(f"OBJECTIVE_VALUE: {profit}")
