import csv, os
import gurobi_pulp_compat as pulp


def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    toys = list(csv.DictReader(open(os.path.join(data_dir, 'table_1.csv'))))
    p = {r['Parameter_Name']: float(r['Value']) for r in csv.DictReader(open(os.path.join(data_dir, 'general_parameters.csv')))}
    periods = [1,2]
    names = [t['Toy_Type'] for t in toys]
    labor = {t['Toy_Type']: float(t['Manufacturing_Labor_Hours']) for t in toys}
    insp = {t['Toy_Type']: float(t['Inspection_Hours']) for t in toys}
    profit = {t['Toy_Type']: float(t['Profit_Per_Unit']) for t in toys}
    demand = {
        ('High-End',1):p['max_demand_high_end_period1'], ('Mid-Range',1):p['max_demand_mid_range_period1'], ('Low-End',1):p['max_demand_low_end_period1'],
        ('High-End',2):p['max_demand_high_end_period2'], ('Mid-Range',2):p['max_demand_mid_range_period2'], ('Low-End',2):p['max_demand_low_end_period2']}
    prob = pulp.LpProblem('ToySeasonFatigue', pulp.LpMaximize)
    x = pulp.LpVariable.dicts('x', (names, periods), lowBound=0)
    ot = pulp.LpVariable.dicts('ot', periods, lowBound=0)
    fatigue = pulp.LpVariable('fatigue', cat='Binary')
    review = pulp.LpVariable('review', cat='Binary')
    prob += (pulp.lpSum(profit[n]*x[n][q] for n in names for q in periods)
             - p['overtime_labor_cost']*pulp.lpSum(ot[q] for q in periods)
             - p['seasonal_safety_review_fee']*review)
    prob += pulp.lpSum(labor[n]*x[n][1] for n in names) <= p['available_labor_hours_period1'] + ot[1]
    prob += pulp.lpSum(labor[n]*x[n][2] for n in names) <= p['available_labor_hours_period2'] - p['period2_labor_recovery_loss']*fatigue + ot[2]
    for q in periods:
        prob += pulp.lpSum(insp[n]*x[n][q] for n in names) <= p[f'available_inspection_hours_period{q}']
        for n in names:
            prob += x[n][q] <= demand[n,q]
    prob += ot[1] + ot[2] <= p['overtime_labor_cap']
    prob += ot[1] <= p['period1_overtime_fatigue_threshold'] + p['overtime_labor_cap']*fatigue
    prob += ot[1] + ot[2] <= p['overtime_review_threshold'] + p['overtime_labor_cap']*review
    prob.solve(pulp.GUROBI_CMD(msg=0))
    print(f"OBJECTIVE_VALUE: {pulp.value(prob.objective)}")

if __name__ == '__main__': main()
