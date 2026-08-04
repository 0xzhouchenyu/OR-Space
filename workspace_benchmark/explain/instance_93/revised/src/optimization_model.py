import os
import pandas as pd
import gurobi_pulp_compat as pulp


def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    df = pd.read_csv(os.path.join(data_dir, 'general_parameters.csv'))
    p = {r['Parameter_Name']: float(r['Value']) for _, r in df.iterrows()}
    prob = pulp.LpProblem('DairyColdChain', pulp.LpMaximize)
    b1 = pulp.LpVariable('barrels_A1', lowBound=0)
    b2 = pulp.LpVariable('barrels_A2', lowBound=0)
    b3 = pulp.LpVariable('barrels_A3', lowBound=0)
    run3 = pulp.LpVariable('run_A3', cat='Binary')
    bonus = pulp.LpVariable('cold_bonus', cat='Binary')
    kg1, kg2, kg3 = p['product_A1_yield']*b1, p['product_A2_yield']*b2, p['product_A3_yield']*b3
    prob += p['profit_per_kg_A1']*kg1 + p['profit_per_kg_A2']*kg2 + p['profit_per_kg_A3']*kg3 + p['cold_chain_bonus_yuan']*bonus
    prob += b1 + b2 + b3 <= p['daily_milk_supply']
    prob += p['product_A1_time']*b1 + p['product_A2_time']*b2 + p['product_A3_time']*b3 <= p['daily_labor_hours']
    prob += kg1 + kg3 <= p['cap_A_shared'] - p['type_A_cleaning_loss_if_A3']*run3
    prob += kg2 >= p['min_A2_kg']
    prob += kg3 >= p['min_A3_kg']
    prob += kg3 <= p['daily_milk_supply'] * p['product_A3_yield'] * run3
    prob += kg3 >= p['min_A3_kg'] * run3
    prob += kg3 >= p['cold_chain_bonus_threshold_kg'] * bonus
    prob += bonus <= run3
    prob.solve(pulp.GUROBI_CMD(msg=0))
    print(f"OBJECTIVE_VALUE: {pulp.value(prob.objective)}")

if __name__ == '__main__': main()
