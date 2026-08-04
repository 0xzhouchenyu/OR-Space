import os
import pandas as pd
from gurobi_pulp_compat import LpProblem, LpMinimize, LpVariable, lpSum, GUROBI_CMD, LpStatus, value


def load_demand(path):
    df = pd.read_csv(path)
    return df['Required_Nurses'].astype(int).tolist()


def load_parameters(path):
    df = pd.read_csv(path)
    params = {}
    for _, row in df.iterrows():
        params[str(row['Parameter_Name'])] = str(row['Value'])
    return params


def parse_index_list(text):
    return [int(x) for x in str(text).split(';') if str(x).strip() != '']


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, '..', 'data')

    demand = load_demand(os.path.join(data_dir, 'table_1.csv'))
    params = load_parameters(os.path.join(data_dir, 'general_parameters.csv'))

    shift_duration = int(float(params['shift_duration']))
    regular_pay = float(params['regular_nurse_pay'])
    contract_pay = float(params['contract_nurse_pay'])
    outsourced_regular_start_index = int(float(params['outsourced_regular_start_index']))
    banned_contract_start_index = int(float(params['banned_contract_start_index']))
    max_total_contract_starts = int(float(params['max_total_contract_starts']))
    min_regular_daytime_coverage = int(float(params['min_regular_daytime_coverage']))
    daytime_period_indices = parse_index_list(params['daytime_period_indices'])

    num_periods = len(demand)
    shift_starts = list(range(num_periods))

    cover_periods = {j: [j, (j + 1) % num_periods] for j in shift_starts}

    prob = LpProblem('NurseScheduling_Revised', LpMinimize)

    x = {
        j: LpVariable(f'x_{j}', lowBound=0, cat='Integer')
        for j in shift_starts if j != outsourced_regular_start_index
    }
    y = {
        j: LpVariable(f'y_{j}', lowBound=0, cat='Integer')
        for j in shift_starts if j != banned_contract_start_index
    }

    prob += lpSum((regular_pay * shift_duration) * x[j] for j in x) + lpSum((contract_pay * shift_duration) * y[j] for j in y)

    for i in range(num_periods):
        regular_cover = lpSum(x[j] for j in x if i in cover_periods[j])
        contract_cover = lpSum(y[j] for j in y if i in cover_periods[j])
        prob += regular_cover + contract_cover >= demand[i], f'demand_{i}'

    for i in daytime_period_indices:
        regular_cover = lpSum(x[j] for j in x if i in cover_periods[j])
        prob += regular_cover >= min_regular_daytime_coverage, f'min_regular_daytime_{i}'

    prob += lpSum(y[j] for j in y) <= max_total_contract_starts, 'contract_cap'

    prob.solve(GUROBI_CMD(msg=0))

    if LpStatus[prob.status] != 'Optimal':
        raise RuntimeError(f'Solver did not find optimal solution. Status: {LpStatus[prob.status]}')

    obj = float(value(prob.objective))
    print(f'OBJECTIVE_VALUE: {obj:.1f}')


if __name__ == '__main__':
    main()