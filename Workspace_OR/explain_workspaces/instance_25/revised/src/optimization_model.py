import os
import pandas as pd
import gurobi_pulp_compat as pulp


def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    df = pd.read_csv(os.path.join(data_dir, 'general_parameters.csv'))
    p = {r['Parameter_Name']: float(r['Value']) for _, r in df.iterrows()}
    W, r1, r2 = p['initial_investment'], p['return_rate_option_1'], p['return_rate_option_2']
    prob = pulp.LpProblem('InvestmentLateSettlement', pulp.LpMaximize)
    x01 = pulp.LpVariable('x01', lowBound=0)
    x02 = pulp.LpVariable('x02', lowBound=0)
    x11 = pulp.LpVariable('x11', lowBound=0)
    x12 = pulp.LpVariable('x12', lowBound=0)
    x21 = pulp.LpVariable('x21', lowBound=0)
    c0 = pulp.LpVariable('c0', lowBound=0)
    rsv1 = pulp.LpVariable('reserve1', lowBound=p['min_reserve_year1'])
    rsv2 = pulp.LpVariable('reserve2', lowBound=p['min_reserve_year2'])
    terminal = pulp.LpVariable('terminal', lowBound=0)
    prob += x01 + x02 + c0 == W
    prob += x11 + x12 + rsv1 == c0 + x01 * (1 + r1)
    # Year-0 two-year proceeds arrive after this allocation window.
    prob += x21 + rsv2 == rsv1 + x11 * (1 + r1)
    prob += x02 <= p['max_option2_start']
    prob += x12 <= p['max_option2_start']
    late_x02 = x02 * (1 + r2) * (1 - p['option2_year0_late_settlement_rate'])
    prob += terminal == rsv2 + x21 * (1 + r1) + x12 * (1 + r2) + late_x02
    prob += terminal
    prob.solve(pulp.GUROBI_CMD(msg=0))
    print(f"OBJECTIVE_VALUE: {pulp.value(prob.objective)}")

if __name__ == '__main__':
    main()
