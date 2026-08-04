import os
import pandas as pd
from gurobi_pulp_compat import LpProblem, LpMaximize, LpVariable, lpSum, LpBinary, GUROBI_CMD, value, LpStatusOptimal


def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    params_df = pd.read_csv(os.path.join(data_dir, 'general_parameters.csv'))
    params = dict(zip(params_df['Parameter_Name'].astype(str).str.strip(), params_df['Value'].astype(float)))
    total_space = params['mall_total_space']
    rent_pct = params['rent_percentage'] / 100.0
    common_area_factor = params['common_area_factor']
    gm_third_cost = params['general_merchandise_third_store_concession']
    catering_security_threshold = params['catering_third_store_security_threshold']
    catering_security_cost = params['catering_third_store_security_cost']

    stores_df = pd.read_csv(os.path.join(data_dir, 'table_1.csv'))
    stores = []
    for _, row in stores_df.iterrows():
        profits = {}
        for k in [1, 2, 3]:
            col = 'Profit_1_Store' if k == 1 else f'Profit_{k}_Stores'
            raw = str(row[col]).strip() if col in row else '-'
            if raw not in {'-', 'nan'}:
                profits[k] = float(raw)
        stores.append({
            'name': str(row['Store_Type']).strip(),
            'area': float(row['Area_per_Shop_m2']),
            'min': int(row['Min']),
            'max': int(row['Max']),
            'profits': profits,
        })

    model = LpProblem('Mall_Optimization_With_Anchor_Concession', LpMaximize)
    x = {}
    for i, s in enumerate(stores):
        for k in range(s['min'], s['max'] + 1):
            if k == 0 or k in s['profits']:
                x[(i, k)] = LpVariable(f'x_{i}_{k}', cat=LpBinary)

    for i, s in enumerate(stores):
        model += lpSum(x[(i, k)] for k in range(s['min'], s['max'] + 1) if (i, k) in x) == 1
    model += lpSum(
        k * s['area'] * common_area_factor * x[(i, k)]
        for i, s in enumerate(stores)
        for k in range(s['min'], s['max'] + 1)
        if (i, k) in x
    ) <= total_space

    gm_idx = next(i for i, s in enumerate(stores) if s['name'] == 'General_Merchandise')
    catering_idx = next(i for i, s in enumerate(stores) if s['name'] == 'Catering')
    catering_security = LpVariable('catering_third_store_security', cat=LpBinary)
    model += lpSum(k * x[(gm_idx, k)] for k in range(stores[gm_idx]['min'], stores[gm_idx]['max'] + 1) if (gm_idx, k) in x) >= 1
    catering_count = lpSum(k * x[(catering_idx, k)] for k in range(stores[catering_idx]['min'], stores[catering_idx]['max'] + 1) if (catering_idx, k) in x)
    model += catering_security >= catering_count - catering_security_threshold

    income = lpSum(
        k * s['profits'][k] * rent_pct * x[(i, k)]
        for i, s in enumerate(stores)
        for k in range(1, s['max'] + 1)
        if (i, k) in x and k in s['profits']
    )
    model += income - gm_third_cost * x[(gm_idx, 3)] - catering_security_cost * catering_security

    status = model.solve(GUROBI_CMD(msg=False))
    if status != LpStatusOptimal:
        raise RuntimeError('Solver did not find an optimal solution.')
    print(f"OBJECTIVE_VALUE: {value(model.objective)}")


if __name__ == '__main__':
    main()
