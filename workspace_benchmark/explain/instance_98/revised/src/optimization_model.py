import os
import csv
from gurobi_pulp_compat import *


def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    products = []
    with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
        products = list(csv.DictReader(f))
    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
        for row in csv.DictReader(f):
            params[row['Parameter_Name']] = float(row['Value'])

    prob = LpProblem('Production_Overtime_Review', LpMaximize)
    x = {p['Product']: LpVariable(f"x_{p['Product']}", lowBound=0) for p in products}
    y = {p['Product']: LpVariable(f"y_{p['Product']}", cat='Binary') for p in products}
    overtime = LpVariable('overtime', lowBound=0, upBound=params['max_overtime'])
    review = LpVariable('overtime_review', cat='Binary')
    product_A_line_audit = LpVariable('product_A_line_audit', cat='Binary')

    prob += (
        lpSum(float(p['Profit_yuan']) * x[p['Product']] for p in products)
        - lpSum(float(p['Setup_Cost_yuan']) * y[p['Product']] for p in products)
        - params['overtime_pay'] * overtime
        - params['overtime_review_fee'] * review
        - params['product_A_line_audit_fee'] * product_A_line_audit
    )
    prob += lpSum(float(p['Steel_Required_kg']) * x[p['Product']] for p in products) <= params['available_steel']
    prob += lpSum(float(p['Aluminum_Required_kg']) * x[p['Product']] for p in products) <= params['available_aluminum']
    prob += lpSum(float(p['Labor_Required_hours']) * x[p['Product']] for p in products) <= params['available_labor'] + overtime
    for p in products:
        prob += x[p['Product']] <= 10000 * y[p['Product']]
    prob += overtime <= params['overtime_review_threshold'] + params['max_overtime'] * review
    prob += x['A'] <= params['product_A_line_audit_threshold'] + 10000 * product_A_line_audit

    prob.solve(GUROBI_CMD(msg=0))
    print(f"OBJECTIVE_VALUE: {value(prob.objective)}")


if __name__ == '__main__':
    main()
