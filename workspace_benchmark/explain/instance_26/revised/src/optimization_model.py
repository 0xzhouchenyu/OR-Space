import os
import pandas as pd
from gurobi_pulp_compat import LpProblem, LpVariable, LpMinimize, lpSum, GUROBI_CMD, value

def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

    # Read staffing requirements
    df_req = pd.read_csv(os.path.join(data_dir, 'table_1.csv'))
    req_values = [int(v) for v in df_req['Required_Salespeople'].tolist()]
    periods = df_req['Time_Period'].tolist()
    n = len(periods)

    # Read general parameters
    df_params = pd.read_csv(os.path.join(data_dir, 'general_parameters.csv'))
    params = {row['Parameter_Name']: row['Value'] for _, row in df_params.iterrows()}

    full_time_cost = float(params['full_time_cost'])
    part_time_cost = float(params['part_time_cost'])
    part_time_cap = int(float(params['part_time_cap_per_period']))
    min_ft_per_period = int(float(params['min_full_time_per_period']))

    prob = LpProblem("MinStaffCost", LpMinimize)

    x_FT = [LpVariable(f"xFT_{i}", lowBound=0, cat='Integer') for i in range(n)]
    x_PT = [LpVariable(f"xPT_{j}", lowBound=0, cat='Integer') for j in range(n)]

    # Objective
    prob += full_time_cost * lpSum(x_FT) + part_time_cost * lpSum(x_PT)

    # Coverage: FT covering period j are shifts j and (j-1) mod n; plus PT in period j
    for j in range(n):
        prob += x_FT[j] + x_FT[(j - 1) % n] + x_PT[j] >= req_values[j], f"demand_{j}"

    # Part-time cap per period
    for j in range(n):
        prob += x_PT[j] <= part_time_cap, f"pt_cap_{j}"

    # Minimum full-time anchor per period
    for j in range(n):
        prob += x_FT[j] + x_FT[(j - 1) % n] >= min_ft_per_period, f"ft_min_{j}"

    prob.solve(GUROBI_CMD(msg=0))

    obj_val = value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()
