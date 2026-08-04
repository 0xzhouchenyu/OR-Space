import os
import pandas as pd
from gurobi_pulp_compat import LpProblem, LpVariable, LpMinimize, LpStatus, lpSum, value, GUROBI_CMD

def main():
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    students_df = pd.read_csv(os.path.join(base, 'table_1.csv'))
    params_df = pd.read_csv(os.path.join(base, 'general_parameters.csv'), engine='python', on_bad_lines='skip')

    params = {}
    for _, row in params_df.iterrows():
        name = str(row['Parameter_Name']).strip()
        v = row['Value']
        try:
            params[name] = float(v)
        except (ValueError, TypeError):
            params[name] = v

    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    student_ids = [int(s) for s in students_df['Student_ID'].tolist()]
    wage = {int(r['Student_ID']): float(r['Wage_CNY_per_hour']) for _, r in students_df.iterrows()}
    avail = {(int(r['Student_ID']), d): float(r[d]) for _, r in students_df.iterrows() for d in days}

    grad_students = {5, 6}
    hours_per_day = 14
    min_undergrad = int(params.get('min_undergrad_hours', 8))
    min_grad = int(params.get('min_grad_hours', 7))
    max_shifts = int(params.get('max_shifts_per_student', 2))
    max_students_day = int(params.get('max_students_per_day', 3))
    min_grad_weekly = float(params.get('min_grad_weekly_coverage_hours', 16))
    open_fee = float(params.get('daily_open_fee_cny', 12))

    prob = LpProblem('Lab_Scheduling_Revised', LpMinimize)

    x = {}
    y = {}
    z = {}
    for i in student_ids:
        for d in days:
            x[i, d] = LpVariable(f'x_{i}_{d}', lowBound=0, upBound=avail[i, d])
            y[i, d] = LpVariable(f'y_{i}_{d}', cat='Binary')
            z[i, d] = LpVariable(f'z_{i}_{d}', cat='Binary')

    prob += (lpSum(wage[i] * x[i, d] for i in student_ids for d in days)
             + open_fee * lpSum(z[i, d] for i in student_ids for d in days))

    for d in days:
        prob += lpSum(x[i, d] for i in student_ids) == hours_per_day

    for i in student_ids:
        for d in days:
            prob += x[i, d] <= avail[i, d] * y[i, d]
            prob += z[i, d] == y[i, d]

    for i in student_ids:
        prob += lpSum(y[i, d] for d in days) <= max_shifts

    for d in days:
        prob += lpSum(y[i, d] for i in student_ids) <= max_students_day

    for i in student_ids:
        min_h = min_grad if i in grad_students else min_undergrad
        prob += lpSum(x[i, d] for d in days) >= min_h

    # NEW: weekly graduate coverage
    prob += lpSum(x[i, d] for i in grad_students for d in days) >= min_grad_weekly

    prob.solve(GUROBI_CMD(msg=0))
    status = LpStatus[prob.status]
    if status != 'Optimal':
        raise RuntimeError(f'Not optimal: {status}')
    obj = value(prob.objective)
    print(f'Status: {status}')
    print(f'OBJECTIVE_VALUE: {obj}')

if __name__ == '__main__':
    main()
