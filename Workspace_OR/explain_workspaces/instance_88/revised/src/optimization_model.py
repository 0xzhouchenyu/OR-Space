import os
import pandas as pd
import gurobi_pulp_compat as pulp


def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    p = {r['Parameter_Name']: float(r['Value']) for _, r in pd.read_csv(os.path.join(data_dir, 'general_parameters.csv')).iterrows()}
    prob = pulp.LpProblem('FertilizerReserveScore', pulp.LpMaximize)
    xl = pulp.LpVariable('liquid_prod', lowBound=0); xs = pulp.LpVariable('solid_prod', lowBound=0)
    y1 = pulp.LpVariable('machine1_extended', cat='Binary'); y2 = pulp.LpVariable('machine2_extended', cat='Binary')
    end_l = p['initial_liquid_inventory'] + xl - p['forecast_liquid_demand']
    end_s = p['initial_solid_inventory'] + xs - p['forecast_solid_demand']
    pri_l = pulp.LpVariable('priority_liquid', lowBound=0, upBound=p['priority_reserve_lots'])
    pri_s = pulp.LpVariable('priority_solid', lowBound=0, upBound=p['priority_reserve_lots'])
    exc_l = pulp.LpVariable('excess_liquid', lowBound=0); exc_s = pulp.LpVariable('excess_solid', lowBound=0)
    prob += pri_l + pri_s + p['excess_reserve_credit']*(exc_l+exc_s) - p['extended_mode_penalty']*(y1+y2)
    prob += p['machine_1_time_per_liquid_lot']*xl + p['machine_1_time_per_solid_lot']*xs <= p['machine_1_available_time']*60 + p['extended_extra_minutes']*y1
    prob += p['machine_2_time_per_liquid_lot']*xl + p['machine_2_time_per_solid_lot']*xs <= p['machine_2_available_time']*60 + p['extended_extra_minutes']*y2
    prob += p['labor_hours_per_machine_extended']*(y1+y2) <= p['labor_budget_hours']
    prob += end_l >= 0; prob += end_s >= 0
    prob += pri_l + exc_l == end_l; prob += pri_s + exc_s == end_s
    prob.solve(pulp.GUROBI_CMD(msg=0))
    print(f"OBJECTIVE_VALUE: {round(pulp.value(prob.objective), 4)}")

if __name__ == '__main__': main()
