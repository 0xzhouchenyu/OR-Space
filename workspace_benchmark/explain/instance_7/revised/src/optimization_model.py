import os
import pandas as pd
import gurobi_pulp_compat as pulp


def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    wh = pd.read_csv(os.path.join(data_dir, 'table_1.csv'))
    ports = pd.read_csv(os.path.join(data_dir, 'table_2.csv'))
    dist = pd.read_csv(os.path.join(data_dir, 'table_3.csv'))
    sp = pd.read_csv(os.path.join(data_dir, 'shortage_penalty.csv'))
    gp = {r['Parameter_Name']: float(r['Value']) for _, r in pd.read_csv(os.path.join(data_dir, 'general_parameters.csv')).iterrows()}
    warehouses = wh['Warehouse'].tolist(); port_names = ports['Port'].tolist()
    supply = dict(zip(wh['Warehouse'], wh['Empty_Containers']))
    demand = dict(zip(ports['Port'], ports['Container_Demand']))
    d = {(r['Warehouse'], p): float(r[p]) for _, r in dist.iterrows() for p in port_names}
    charge = dict(zip(sp['Port'], sp['Shortage_Charge']))
    grace = dict(zip(sp['Port'], sp['Grace_Containers']))
    fee = dict(zip(sp['Port'], sp['Recovery_Fee']))
    prob = pulp.LpProblem('ContainerRecoveryCost', pulp.LpMinimize)
    x = pulp.LpVariable.dicts('ship', (warehouses, port_names), lowBound=0)
    short = pulp.LpVariable.dicts('short', port_names, lowBound=0)
    rec = pulp.LpVariable.dicts('recovery', port_names, cat='Binary')
    pool = pulp.LpVariable('adriatic_pool', cat='Binary')
    transport = pulp.lpSum(gp['cost_per_km'] * d[w,p] * x[w][p] for w in warehouses for p in port_names)
    local = pulp.lpSum(charge[p] * short[p] + fee[p] * rec[p] for p in port_names)
    prob += transport + local + gp['adriatic_pool_recovery_fee'] * pool
    for w in warehouses:
        prob += pulp.lpSum(x[w][p] for p in port_names) <= supply[w]
    for p in port_names:
        prob += pulp.lpSum(x[w][p] for w in warehouses) + short[p] == demand[p]
        prob += short[p] <= grace[p] + demand[p] * rec[p]
    adriatic = ['Venice','Ancona','Bari']
    prob += pulp.lpSum(short[p] for p in adriatic) <= gp['adriatic_pool_shortage_trigger'] + sum(demand[p] for p in adriatic) * pool
    prob.solve(pulp.GUROBI_CMD(msg=0))
    print(f"OBJECTIVE_VALUE: {pulp.value(prob.objective)}")

if __name__ == '__main__': main()
