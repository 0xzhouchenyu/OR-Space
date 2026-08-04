import os
import csv
from gurobi_pulp_compat import LpProblem, LpMaximize, LpVariable, lpSum, LpBinary, GUROBI_CMD, LpStatus, value


def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name'].strip()] = float(row['Value'].strip())

    profit_corn = params['profit_per_acre_corn']
    profit_wheat = params['profit_per_acre_wheat']
    profit_soybeans = params['profit_per_acre_soybeans']
    profit_sorghum = params['profit_per_acre_sorghum']
    total_area = params['total_farm_area']
    corn_wheat_ratio = params['corn_wheat_ratio']
    soybeans_sorghum_ratio = params['soybeans_sorghum_ratio']
    wheat_sorghum_ratio = params['wheat_sorghum_ratio']

    min_corn_acres = 20.0

    prob = LpProblem('Farm_Optimization_Revised', LpMaximize)

    corn = LpVariable('corn', lowBound=0)
    wheat = LpVariable('wheat', lowBound=0)
    soybeans = LpVariable('soybeans', lowBound=0)
    sorghum = LpVariable('sorghum', lowBound=0)

    y_corn = LpVariable('y_corn', cat=LpBinary)
    y_soybeans = LpVariable('y_soybeans', cat=LpBinary)

    prob += profit_corn * corn + profit_wheat * wheat + profit_soybeans * soybeans + profit_sorghum * sorghum

    prob += corn + wheat + soybeans + sorghum <= total_area, 'total_area'
    prob += corn >= corn_wheat_ratio * wheat, 'corn_wheat_ratio'
    prob += soybeans >= soybeans_sorghum_ratio * sorghum, 'soybeans_sorghum_ratio'
    prob += wheat == wheat_sorghum_ratio * sorghum, 'wheat_sorghum_ratio'

    prob += corn >= min_corn_acres, 'corn_min_supply'

    prob += corn <= total_area * y_corn, 'corn_activation'
    prob += soybeans <= total_area * y_soybeans, 'soybeans_activation'
    prob += y_corn + y_soybeans <= 1, 'mutual_exclusion_corn_soybeans'

    prob.solve(GUROBI_CMD(msg=0))

    value_obj = value(prob.objective)
    print(f'OBJECTIVE_VALUE: {value_obj}')


if __name__ == '__main__':
    main()
