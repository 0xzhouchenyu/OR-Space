import os
import pandas as pd
from gurobi_pulp_compat import LpProblem, LpMinimize, LpVariable, lpSum, GUROBI_CMD, LpStatus, value


def solve():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, '..', 'data')

    df_dist = pd.read_csv(os.path.join(data_dir, 'table_1.csv'))
    df_params = pd.read_csv(os.path.join(data_dir, 'general_parameters.csv'))

    params = {row['Parameter_Name']: float(row['Value']) for _, row in df_params.iterrows()}

    routes = []
    distances = {}
    coal_yards = sorted(df_dist['Coal_Yard'].astype(str).unique().tolist())
    areas = sorted(df_dist['Residential_Area'].astype(int).unique().tolist())

    for _, row in df_dist.iterrows():
        yard = str(row['Coal_Yard'])
        area = int(row['Residential_Area'])
        routes.append((yard, area))
        distances[(yard, area)] = float(row['Distance_km'])

    demand = {
        1: params['residential_area_1_demand'],
        2: params['residential_area_2_demand'],
        3: params['residential_area_3_demand']
    }

    min_supply = {
        'A': params['min_coal_yard_A'],
        'B': params['min_coal_yard_B_adjusted']
    }

    min_share_area3_from_A = params['min_share_area3_from_A']
    area3_staging_threshold = params['area3_A_staging_threshold']
    area3_excess_cost = params['area3_A_excess_staging_cost']

    prob = LpProblem('Coal_Distribution_Revised', LpMinimize)

    x = {r: LpVariable(f'x_{r[0]}_{r[1]}', lowBound=0) for r in routes}
    area3_excess = LpVariable('area3_A_staging_excess', lowBound=0)

    prob += lpSum(distances[r] * x[r] for r in routes) + area3_excess_cost * area3_excess

    for yard in coal_yards:
        yard_routes = [r for r in routes if r[0] == yard]
        prob += lpSum(x[r] for r in yard_routes) >= min_supply[yard], f'min_dispatch_{yard}'

    for area in [1, 2, 3]:
        area_routes = [r for r in routes if r[1] == area]
        prob += lpSum(x[r] for r in area_routes) == demand[area], f'demand_{area}'

    prob += x[('A', 3)] >= min_share_area3_from_A * demand[3], 'area3_min_share_from_A'
    prob += area3_excess >= x[('A', 3)] - area3_staging_threshold, 'area3_A_staging_excess'

    solver = GUROBI_CMD(msg=0)
    prob.solve(solver)

    if LpStatus[prob.status] != 'Optimal':
        raise RuntimeError(f'Solver ended with status {LpStatus[prob.status]}')

    print(f'OBJECTIVE_VALUE: {value(prob.objective):.1f}')


if __name__ == '__main__':
    solve()
