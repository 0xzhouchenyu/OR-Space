import csv, os
import gurobi_pulp_compat as pulp


def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    p = {r['Parameter_Name']: float(r['Value']) for r in csv.DictReader(open(os.path.join(data_dir, 'general_parameters.csv')))}
    prob = pulp.LpProblem('OilThresholdCommercials', pulp.LpMaximize)
    a1 = pulp.LpVariable('A_to_I', lowBound=0); a2 = pulp.LpVariable('A_to_II', lowBound=0)
    b1 = pulp.LpVariable('B_to_I', lowBound=0); b2 = pulp.LpVariable('B_to_II', lowBound=0)
    p1 = pulp.LpVariable('purchase_block1', lowBound=0, upBound=500)
    p2 = pulp.LpVariable('purchase_block2', lowBound=0, upBound=500)
    p3 = pulp.LpVariable('purchase_block3', lowBound=0, upBound=500)
    y2 = pulp.LpVariable('block2_open', cat='Binary'); y3 = pulp.LpVariable('block3_open', cat='Binary')
    premium = pulp.LpVariable('typeII_uplift', cat='Binary')
    prem_out = pulp.LpVariable('premium_typeII_output', lowBound=0)
    rebate = pulp.LpVariable('bulk_rebate', cat='Binary')
    outI, outII = a1+b1, a2+b2
    total_purchase = p1+p2+p3
    prob += p2 <= 500*y2; prob += p1 >= 500*y2
    prob += p3 <= 500*y3; prob += p2 >= 500*y3
    prob += total_purchase <= p['max_purchase_crude_A']
    prob += a1+a2 <= p['inventory_crude_A'] + total_purchase
    prob += b1+b2 <= p['inventory_crude_B']
    prob += a1 >= p['min_proportion_crude_A_type_I']/100 * outI
    prob += a2 >= p['min_proportion_crude_A_type_II']/100 * outII
    prob += outI+outII <= p['processing_capacity']; prob += outI+outII >= p['min_total_gasoline_output']
    M = p['processing_capacity']
    prob += outII >= p['type_II_contract_threshold'] * premium
    prob += prem_out <= outII; prob += prem_out <= M*premium; prob += prem_out >= outII - M*(1-premium)
    prob += total_purchase <= p['bulk_purchase_rebate_threshold'] + p['max_purchase_crude_A']*rebate
    revenue = p['selling_price_type_I']*outI + p['selling_price_type_II']*outII + p['type_II_price_lift']*prem_out
    purchase = p['market_price_crude_A_tier_1']*p1 + p['market_price_crude_A_tier_2']*p2 + p['market_price_crude_A_tier_3']*p3
    processing = p['processing_cost_per_ton']*(outI+outII)
    prob += revenue - purchase - processing + p['bulk_purchase_rebate']*rebate
    prob.solve(pulp.GUROBI_CMD(msg=0))
    print(f"OBJECTIVE_VALUE: {pulp.value(prob.objective)}")

if __name__ == '__main__': main()
