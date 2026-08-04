import pandas as pd
import gurobi_pulp_compat as pulp
from utils import get_data_path

def solve():
    # Load data
    table_1 = pd.read_csv(get_data_path('table_1.csv'))
    table_2 = pd.read_csv(get_data_path('table_2.csv'))
    params = pd.read_csv(get_data_path('general_parameters.csv'))

    # Parse parameters
    min_contract_types = int(params.loc[params['Parameter_Name'] == 'min_contract_types', 'Value'].values[0])
    max_contract_types = int(params.loc[params['Parameter_Name'] == 'max_contract_types', 'Value'].values[0])
    mutual_exclusion = str(params.loc[params['Parameter_Name'] == 'mutual_exclusion_1_and_4', 'Value'].values[0]).strip().lower() == 'true'

    # Convert required area to units of 100 ㎡
    demands = {int(row['Month']): float(row['Required_area_㎡']) / 100.0 for _, row in table_1.iterrows()}
    costs = {int(row['Contract_length_months']): float(row['Rental_fee_per_100㎡_yuan']) for _, row in table_2.iterrows()}

    months = list(demands.keys())
    max_month = max(months)

    # Initialize model
    prob = pulp.LpProblem("Warehouse_Rental", pulp.LpMinimize)

    # Variables
    # x[i, j] = number of 100 sqm units rented starting at month i for j months
    x = pulp.LpVariable.dicts("x", [(i, j) for i in months for j in costs.keys() if i + j - 1 <= max_month], lowBound=0, cat='Integer')
    
    # y[j] = 1 if contract length j is used, 0 otherwise
    y = pulp.LpVariable.dicts("y", costs.keys(), cat='Binary')

    # Objective: Minimize total rental cost
    prob += pulp.lpSum(costs[j] * x[i, j] for (i, j) in x)

    # Constraints
    # 1. Demand fulfillment for each month
    for m in months:
        prob += pulp.lpSum(x[i, j] for (i, j) in x if i <= m and i + j - 1 >= m) == demands[m]

    # 2. Link continuous variables x to binary variables y
    M = sum(demands.values())
    for j in costs.keys():
        prob += pulp.lpSum(x[i, j] for i in months if (i, j) in x) <= M * y[j]
        prob += pulp.lpSum(x[i, j] for i in months if (i, j) in x) >= y[j]

    # 3. Contract types limits
    prob += pulp.lpSum(y[j] for j in costs.keys()) >= min_contract_types
    prob += pulp.lpSum(y[j] for j in costs.keys()) <= max_contract_types

    # 4. Mutual exclusion between 1-month and 4-month contracts
    if mutual_exclusion:
        if 1 in y and 4 in y:
            prob += y[1] + y[4] <= 1

    # Solve the problem
    prob.solve(pulp.GUROBI_CMD(msg=False))

    # Output the objective value
    print(f"OBJECTIVE_VALUE: {pulp.value(prob.objective)}")

if __name__ == "__main__":
    solve()