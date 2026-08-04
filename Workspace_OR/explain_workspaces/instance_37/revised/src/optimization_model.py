import csv, os
import gurobi_pulp_compat as pulp


def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    rows = list(csv.reader(open(os.path.join(data_dir, 'table_1.csv'))))[1:]
    aI, bI = float(rows[0][1]), float(rows[0][2])
    aII, bII = float(rows[1][1]), float(rows[1][2])
    profA, profB = float(rows[2][1]), float(rows[2][2])
    p = {r['Parameter_Name']: float(r['Value']) for r in csv.DictReader(open(os.path.join(data_dir, 'general_parameters.csv')))}
    prob = pulp.LpProblem('TwoWeekRecovery', pulp.LpMaximize)
    weeks = [1, 2]
    xA = pulp.LpVariable.dicts('A', weeks, lowBound=0)
    xB = pulp.LpVariable.dicts('B', weeks, lowBound=0)
    otI = pulp.LpVariable.dicts('otI', weeks, lowBound=0)
    otII = pulp.LpVariable.dicts('otII', weeks, lowBound=0)
    recI = pulp.LpVariable('recovery_I', cat='Binary')
    recII = pulp.LpVariable('recovery_II', cat='Binary')
    profit = profA * sum(xA[w] for w in weeks) + profB * sum(xB[w] for w in weeks)
    ot_cost = p['overtime_premium_I'] * sum(otI[w] for w in weeks) + p['overtime_premium_II'] * sum(otII[w] for w in weeks)
    prob += profit - ot_cost
    prob += aI*xA[1] + bI*xB[1] <= p['process_I_hours'] + otI[1]
    prob += aII*xA[1] + bII*xB[1] <= p['process_II_hours'] + otII[1]
    prob += aI*xA[2] + bI*xB[2] <= p['process_I_hours'] - p['week2_recovery_loss_I']*recI + otI[2]
    prob += aII*xA[2] + bII*xB[2] <= p['process_II_hours'] - p['week2_recovery_loss_II']*recII + otII[2]
    for w in weeks:
        prob += otI[w] <= p['max_overtime_I_per_week']
        prob += otII[w] <= p['max_overtime_II_per_week']
    prob += otI[1] <= p['week1_overtime_fatigue_threshold_I'] + p['max_overtime_I_per_week'] * recI
    prob += otII[1] <= p['week1_overtime_fatigue_threshold_II'] + p['max_overtime_II_per_week'] * recII
    prob += xA[1] >= p['week1_min_model_A_units']; prob += xB[1] >= p['week1_min_model_B_units']
    prob += xA[2] >= p['week2_min_model_A_units']; prob += xB[2] >= p['week2_min_model_B_units']
    prob += xA[1] + xA[2] >= p['min_model_A_units']; prob += xB[1] + xB[2] >= p['min_model_B_units']
    totalI = sum(aI*xA[w] + bI*xB[w] for w in weeks)
    totalII = sum(aII*xA[w] + bII*xB[w] for w in weeks)
    prob += totalI >= 2 * p['process_I_hours'] * p['min_avg_utilization_I']
    prob += totalII >= 2 * p['process_II_hours'] * p['min_avg_utilization_II']
    prob += profit - ot_cost >= p['min_weekly_profit']
    prob.solve(pulp.GUROBI_CMD(msg=0))
    print(f"OBJECTIVE_VALUE: {pulp.value(prob.objective)}")

if __name__ == '__main__': main()
