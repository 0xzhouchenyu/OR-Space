import gurobi_pulp_compat as pulp
import pandas as pd
import os

def solve():
    # Read data
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'general_parameters.csv')
    df = pd.read_csv(csv_path)
    params = dict(zip(df['Parameter_Name'], df['Value']))

    commodities = ['steel', 'engine', 'electronics', 'plastic']

    # Variables: Production levels for each commodity
    x = {c: pulp.LpVariable(f"x_{c}", lowBound=0) for c in commodities}

    # Apply production upper bounds if they exist
    for c in commodities:
        for suffix in ['_production_limit', '_limit', '_capacity']:
            key = f"{c}{suffix}"
            if key in params:
                x[c].upBound = params[key]

    # Model
    model = pulp.LpProblem("Maximize_GDP", pulp.LpMaximize)

    # Net export of each commodity = Production - Domestic Consumption
    # Domestic consumption of commodity c = sum over all other commodities c' of (c'_c_requirement * x[c'])
    net_export = {}
    for c in commodities:
        consumed = pulp.lpSum(
            params.get(f"{c_prime}_{c}_requirement", 0.0) * x[c_prime]
            for c_prime in commodities
        )
        net_export[c] = x[c] - consumed

    # Import costs
    imports = pulp.lpSum(params.get(f"{c}_import_cost", 0.0) * x[c] for c in commodities)

    # Objective: GDP = Export revenue - Import costs
    gdp = pulp.lpSum(params[f"{c}_price"] * net_export[c] for c in commodities) - imports
    model += gdp

    # Constraints:
    # 1. Net export >= 0 for each commodity (domestic production must satisfy domestic demand)
    for c in commodities:
        model += net_export[c] >= 0, f"Domestic_Demand_{c}"

    # 2. Labor constraint
    model += pulp.lpSum(
        params.get(f"{c}_labor_requirement", 0.0) * x[c] for c in commodities
    ) <= params['labor_force'], "Labor_Limit"

    # Solve the model
    model.solve(pulp.GUROBI_CMD(msg=False))

    return pulp.value(model.objective)

if __name__ == '__main__':
    result = solve()
    if result is not None:
        print(f"OBJECTIVE_VALUE: {round(result, 3)}")
    else:
        print("OBJECTIVE_VALUE: None")
