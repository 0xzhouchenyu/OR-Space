import os
import pandas as pd
import gurobi_pulp_compat as pulp


def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    df = pd.read_csv(os.path.join(data_dir, 'general_parameters.csv'))
    P = {row['Parameter_Name'].strip(): float(row['Value']) for _, row in df.iterrows()}

    prob = pulp.LpProblem('Promo_With_Display_Review', pulp.LpMaximize)
    x_a = pulp.LpVariable('x_a', lowBound=0, cat='Integer')
    x_b = pulp.LpVariable('x_b', lowBound=0, cat='Integer')
    x_c = pulp.LpVariable('x_c', lowBound=0, cat='Integer')
    y_a = pulp.LpVariable('y_a', cat='Binary')
    y_b = pulp.LpVariable('y_b', cat='Binary')
    y_c = pulp.LpVariable('y_c', cat='Binary')
    review_b = pulp.LpVariable('package_b_review', cat='Binary')
    review_c = pulp.LpVariable('package_c_review', cat='Binary')

    prob += (
        P['package_a_price'] * x_a + P['package_b_price'] * x_b + P['package_c_price'] * x_c
        - P['activation_cost_a'] * y_a - P['activation_cost_b'] * y_b - P['activation_cost_c'] * y_c
        - P['package_b_review_charge'] * review_b
        - P['package_c_review_charge'] * review_c
    )
    prob += P['package_a_shirts'] * x_a + P['package_b_shirts'] * x_b + P['package_c_shirts'] * x_c <= P['shirts_inventory']
    prob += P['package_a_pants'] * x_a + P['package_b_pants'] * x_b + P['package_c_pants'] * x_c <= P['pants_inventory']
    prob += P['labor_hours_per_A'] * x_a + P['labor_hours_per_B'] * x_b + P['labor_hours_per_C'] * x_c <= P['labor_hours_total']

    prob += x_a <= P['bigM_a'] * y_a; prob += x_a >= P['min_campaign_batch_a'] * y_a
    prob += x_b <= P['bigM_b'] * y_b; prob += x_b >= P['min_campaign_batch_b'] * y_b
    prob += x_c <= P['bigM_c'] * y_c; prob += x_c >= P['min_campaign_batch_c'] * y_c
    prob += x_b <= P['package_b_review_threshold'] + P['bigM_b'] * review_b
    prob += x_c <= P['package_c_review_threshold'] + P['bigM_c'] * review_c

    prob.solve(pulp.GUROBI_CMD(msg=0))
    print(f"OBJECTIVE_VALUE: {pulp.value(prob.objective)}")


if __name__ == '__main__':
    main()
