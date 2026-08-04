import csv, os
import gurobi_pulp_compat as pulp


def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    rows = list(csv.reader(open(os.path.join(data_dir, 'table_1.csv'))))
    crops = rows[0][1:]
    data = {r[0]: {crops[i]: float(r[i+1]) for i in range(len(crops))} for r in rows[1:]}
    p = {r['Parameter_Name']: float(r['Value']) for r in csv.DictReader(open(os.path.join(data_dir, 'general_parameters.csv')))}
    prob = pulp.LpProblem('FarmBiosecurity', pulp.LpMaximize)
    x = pulp.LpVariable.dicts('crop', crops, lowBound=0)
    cows = pulp.LpVariable('cows', lowBound=0, upBound=p['max_dairy_cows'])
    chickens = pulp.LpVariable('chickens', lowBound=0, upBound=p['max_chickens'])
    aw_out = pulp.LpVariable('aw_outside', lowBound=0)
    ss_out = pulp.LpVariable('ss_outside', lowBound=0)
    coop = pulp.LpVariable('coop_open', cat='Binary')
    large = pulp.LpVariable('large_flock_review', cat='Binary')
    prob += (pulp.lpSum(data['Annual Net Income (Yuan/hectare)'][c]*x[c] for c in crops)
             + p['net_income_per_dairy_cow']*cows + p['net_income_per_chicken']*chickens
             + p['external_work_rate_autumn_winter']*aw_out + p['external_work_rate_spring_summer']*ss_out
             - p['fixed_cost_chicken_setup']*coop - p['second_biosecurity_cost']*large)
    prob += pulp.lpSum(x[c] for c in crops) + p['land_per_dairy_cow']*cows <= p['land_area']
    prob += p['investment_per_dairy_cow']*cows + p['investment_per_chicken']*chickens <= p['funds_available']
    prob += (pulp.lpSum(data['Person-days (Autumn/Winter)'][c]*x[c] for c in crops)
             + p['labor_autumn_winter_per_dairy_cow']*cows + p['labor_autumn_winter_per_chicken']*chickens
             + p['biosecurity_training_aw_days']*coop + aw_out <= p['labor_autumn_winter'])
    prob += (pulp.lpSum(data['Person-days (Spring/Summer)'][c]*x[c] for c in crops)
             + p['labor_spring_summer_per_dairy_cow']*cows + p['labor_spring_summer_per_chicken']*chickens
             + p['biosecurity_training_ss_days']*coop + ss_out <= p['labor_spring_summer'])
    prob += chickens <= p['max_chickens'] * coop
    prob += chickens >= p['min_chickens_if_coop_open'] * coop
    prob += chickens <= p['second_biosecurity_threshold'] + p['max_chickens'] * large
    prob += large <= coop
    prob.solve(pulp.GUROBI_CMD(msg=0))
    print(f"OBJECTIVE_VALUE: {pulp.value(prob.objective)}")

if __name__ == '__main__': main()
