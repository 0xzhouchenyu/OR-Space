import os
import pandas as pd
import gurobi_pulp_compat as pulp


def params(df):
    return {r['Parameter_Name']: float(r['Value']) for _, r in df.iterrows()}


def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    t1 = pd.read_csv(os.path.join(data_dir, 'table_1.csv'))
    t2 = pd.read_csv(os.path.join(data_dir, 'table_2.csv'))
    t3 = pd.read_csv(os.path.join(data_dir, 'table_3.csv'))
    gp = params(pd.read_csv(os.path.join(data_dir, 'general_parameters.csv')))
    df = t1.merge(t2, on='Product').merge(t3, on='Product')
    products = df['Product'].tolist()
    rows = {r['Product']: r for _, r in df.iterrows()}
    prob = pulp.LpProblem('A1PriorityCalendar', pulp.LpMaximize)
    x = pulp.LpVariable.dicts('x', products, lowBound=0)
    y = pulp.LpVariable.dicts('open', products, cat='Binary')
    watch = pulp.LpVariable('a1_watch', cat='Binary')
    deep = pulp.LpVariable('a1_deep', cat='Binary')
    excess = pulp.LpVariable('a1_priority_excess', lowBound=0)
    margin = pulp.lpSum((rows[p]['Selling_Price'] - rows[p]['Production_Cost']) * x[p] for p in products)
    fixed = pulp.lpSum(rows[p]['Activation_Cost'] * y[p] for p in products)
    uplift = gp['a1_priority_price_lift'] * excess
    charges = gp['a1_quality_release_fee'] * watch + gp['a1_deep_service_fee'] * deep
    prob += margin + uplift - fixed - charges
    for p in products:
        prob += y[p] == 1
        prob += x[p] <= rows[p]['Maximum_Demand'] * y[p]
        prob += x[p] >= rows[p]['Minimum_Batch'] * y[p]
    M = rows['A1']['Maximum_Demand']
    th = gp['a1_watch_threshold']
    deep_th = gp['a1_deep_service_threshold']
    prob += x['A1'] - th <= (M - th) * watch
    prob += x['A1'] - deep_th <= (M - deep_th) * deep
    prob += deep <= watch
    prob += excess >= x['A1'] - th
    prob += excess <= x['A1'] - th + M * (1 - watch)
    prob += excess <= (M - th) * watch
    used_days = pulp.lpSum(x[p] / rows[p]['Production_Quota'] for p in products)
    prob += used_days <= gp['production_days'] - gp['maintenance_penalty_watch'] * watch - gp['maintenance_penalty_deep'] * deep
    prob.solve(pulp.GUROBI_CMD(msg=0))
    print(f"OBJECTIVE_VALUE: {pulp.value(prob.objective)}")

if __name__ == '__main__':
    main()
