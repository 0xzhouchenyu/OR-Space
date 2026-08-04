import os
import pandas as pd
import gurobi_pulp_compat as pulp


def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    prod = pd.read_csv(os.path.join(data_dir, 'table_1.csv'))
    gp = pd.read_csv(os.path.join(data_dir, 'general_parameters.csv'))
    p = {r['Parameter_Name']: float(r['Value']) for _, r in gp.iterrows()}
    data = {}
    for _, r in prod.iterrows():
        cap = None if pd.isna(r['Production_capacity']) or str(r['Production_capacity']).strip()=='' else float(r['Production_capacity'])
        data[r['Product']] = {k: float(r[k]) for k in ['Price_per_pack','Grains_per_pack','Meat_per_pack','Variable_cost_per_pack']}
        data[r['Product']]['cap'] = cap
    m, y = data['Meaties'], data['Yummies']
    cm = m['Price_per_pack'] - m['Variable_cost_per_pack'] - m['Grains_per_pack']*p['price_per_lb_grains'] - m['Meat_per_pack']*p['price_per_lb_meat']
    cy = y['Price_per_pack'] - y['Variable_cost_per_pack'] - y['Grains_per_pack']*p['price_per_lb_grains'] - y['Meat_per_pack']*p['price_per_lb_meat']
    prob = pulp.LpProblem('HealthyPetRetailPair', pulp.LpMaximize)
    xm = pulp.LpVariable('meaties', lowBound=0)
    xy = pulp.LpVariable('yummies', lowBound=0)
    line = pulp.LpVariable('line_open', cat='Binary')
    rebate = pulp.LpVariable('retailer_allowance', cat='Binary')
    prob += cm*xm + cy*xy - p['line_fixed_cost']*line + p['retailer_rebate_fixed']*rebate
    prob += m['Grains_per_pack']*xm + y['Grains_per_pack']*xy <= p['max_grains']
    prob += m['Meat_per_pack']*xm + y['Meat_per_pack']*xy <= p['max_meat']
    prob += xm <= min(m['cap'], p['line_capacity_packs']) * line
    prob += xy <= p['line_capacity_packs'] * line
    prob += xm + xy <= p['line_capacity_packs'] * line
    prob += xm + xy >= p['min_batch_packs'] * line
    prob += xy >= p['min_yummies'] * line
    prob += xy >= p['retailer_rebate_yummies_threshold'] * rebate
    prob += xm >= p['retailer_rebate_min_meaties'] * rebate
    prob += rebate <= line
    prob.solve(pulp.GUROBI_CMD(msg=0))
    print(f"OBJECTIVE_VALUE: {pulp.value(prob.objective)}")

if __name__ == '__main__': main()
