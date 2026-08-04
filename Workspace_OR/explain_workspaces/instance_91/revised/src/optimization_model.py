import os
import csv
import gurobi_pulp_compat as pulp


def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            try:
                params[row['Parameter_Name']] = float(row['Value'])
            except ValueError:
                params[row['Parameter_Name']] = row['Value']

    ratio_A, ratio_B = map(float, str(params['production_ratio_A_to_B']).split(':'))
    A = pulp.LpVariable('Product_A', lowBound=0)
    B = pulp.LpVariable('Product_B', lowBound=0)
    O = pulp.LpVariable('Overtime_Hours', lowBound=0, upBound=params['max_overtime_hours'])
    review = pulp.LpVariable('overtime_review', cat='Binary')
    product_A_senior_batch = pulp.LpVariable('product_A_senior_batch', cat='Binary')
    prob = pulp.LpProblem('ProductMix_OvertimeReview', pulp.LpMaximize)

    prob += (
        params['profit_product_A'] * A
        + params['profit_product_B'] * B
        - params['overtime_penalty_per_hour'] * O
        - params['overtime_review_fee'] * review
        - params['product_A_senior_batch_fee'] * product_A_senior_batch
    )
    prob += params['assembly_time_A'] * A + params['assembly_time_B'] * B <= params['machine_working_time'] * 60 + O * 60
    prob += ratio_B * A - ratio_A * B <= 0
    prob += O <= params['overtime_review_threshold_hours'] + params['max_overtime_hours'] * review
    prob += A <= params['product_A_senior_batch_threshold'] + 10000 * product_A_senior_batch

    prob.solve(pulp.GUROBI_CMD(msg=0))
    print(f"OBJECTIVE_VALUE: {pulp.value(prob.objective)}")


if __name__ == '__main__':
    main()
