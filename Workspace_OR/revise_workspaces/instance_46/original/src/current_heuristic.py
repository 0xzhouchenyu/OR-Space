import os
import csv
from gurobi_pulp_compat import *
from utils import load_data

def main():
    students, params = load_data()
    
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    student_ids = [s['Student_ID'] for s in students]
    
    hours_per_day = 14  # 8AM to 10PM
    min_undergrad = params['min_undergrad_hours']
    min_grad = params['min_grad_hours']
    max_shifts = params['max_shifts_per_student']
    max_students_day = params['max_students_per_day']
    
    # Assume students 5,6 are grad students (higher wages), 1-4 are undergrads
    grad_students = {5, 6}
    
    wage = {s['Student_ID']: s['Wage_CNY_per_hour'] for s in students}
    avail = {(s['Student_ID'], d): s[d] for s in students for d in days}
    
    prob = LpProblem("Lab_Scheduling", LpMinimize)
    
    x = {}  # hours worked
    y = {}  # binary: works on that day
    for i in student_ids:
        for d in days:
            x[i, d] = LpVariable(f"x_{i}_{d}", lowBound=0, upBound=avail[i, d], cat='Continuous')
            y[i, d] = LpVariable(f"y_{i}_{d}", cat='Binary')
    
    # Objective: minimize total wages
    prob += lpSum(wage[i] * x[i, d] for i in student_ids for d in days)
    
    # Coverage: exactly 14 hours per day
    for d in days:
        prob += lpSum(x[i, d] for i in student_ids) == hours_per_day
    
    # Link x and y: if x[i,d] > 0 then y[i,d] = 1
    for i in student_ids:
        for d in days:
            prob += x[i, d] <= avail[i, d] * y[i, d]
            # If y=1 and avail>0, student could work 0 hours, but we don't force them
    
    # Max shifts per student per week
    for i in student_ids:
        prob += lpSum(y[i, d] for d in days) <= max_shifts
    
    # Max students per day
    for d in days:
        prob += lpSum(y[i, d] for i in student_ids) <= max_students_day
    
    # Minimum weekly hours
    for i in student_ids:
        min_h = min_grad if i in grad_students else min_undergrad
        prob += lpSum(x[i, d] for d in days) >= min_h
    
    prob.solve(GUROBI_CMD(msg=0))
    
    obj = value(prob.objective)
    print(f"Status: {LpStatus[prob.status]}")
    for i in student_ids:
        for d in days:
            v = value(x[i, d])
            if v and v > 0.001:
                print(f"  Student {i} on {d}: {v:.1f}h")
    print(f"OBJECTIVE_VALUE: {obj}")

if __name__ == "__main__":
    main()