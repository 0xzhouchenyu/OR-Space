import os
import pandas as pd
import gurobi_pulp_compat as pulp


def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    t1 = pd.read_csv(os.path.join(data_dir, 'table_1.csv'))
    t2 = pd.read_csv(os.path.join(data_dir, 'table_2.csv'))
    gp = pd.read_csv(os.path.join(data_dir, 'general_parameters.csv'))
    val = dict(zip(gp['Parameter_Name'], gp['Value']))
    p = {k: (float(v) if str(v).replace('.','',1).isdigit() else v) for k,v in val.items()}
    demands = {int(r['Month']): float(r['Required_area_㎡'])/100.0 for _, r in t1.iterrows()}
    costs = {int(r['Contract_length_months']): float(r['Rental_fee_per_100㎡_yuan']) for _, r in t2.iterrows()}
    months = sorted(demands); maxm = max(months)
    pairs = [(i,j) for i in months for j in costs if i+j-1 <= maxm]
    M = sum(demands.values()) + len(pairs)
    prob = pulp.LpProblem('WarehouseOnboarding', pulp.LpMinimize)
    x = pulp.LpVariable.dicts('area', pairs, lowBound=0, cat='Integer')
    z = pulp.LpVariable.dicts('active', pairs, cat='Binary')
    e = pulp.LpVariable.dicts('expedite', pairs, cat='Binary')
    y = pulp.LpVariable.dicts('length_used', list(costs), cat='Binary')
    prob += (pulp.lpSum(costs[j]*x[i,j] + float(p['activation_fee_per_contract'])*z[i,j] + float(p['expedited_onboarding_fee'])*e[i,j] for i,j in pairs))
    loss = float(p['onboarding_loss_units'])
    for m in months:
        prob += pulp.lpSum((x[i,j] - loss*z[i,j] + loss*e[i,j]) if m == i else x[i,j] for i,j in pairs if i <= m <= i+j-1) == demands[m]
    for i,j in pairs:
        prob += x[i,j] <= M*z[i,j]
        prob += x[i,j] >= float(p['min_area_per_contract_units'])*z[i,j]
        prob += e[i,j] <= z[i,j]
    for j in costs:
        jpairs = [(i,jj) for i,jj in pairs if jj == j]
        prob += pulp.lpSum(z[i,jj] for i,jj in jpairs) <= M*y[j]
        prob += pulp.lpSum(z[i,jj] for i,jj in jpairs) >= y[j]
    prob += pulp.lpSum(y[j] for j in costs) >= float(p['min_contract_types'])
    prob += pulp.lpSum(y[j] for j in costs) <= float(p['max_contract_types'])
    if str(p['mutual_exclusion_1_and_4']).lower() == 'true':
        prob += y[1] + y[4] <= 1
    for m in months:
        prob += pulp.lpSum(z[i,j] for i,j in pairs if i <= m <= i+j-1) <= float(p['monthly_max_parallel_contracts'])
    prob.solve(pulp.GUROBI_CMD(msg=0))
    print(f"OBJECTIVE_VALUE: {pulp.value(prob.objective)}")

if __name__ == '__main__': main()
