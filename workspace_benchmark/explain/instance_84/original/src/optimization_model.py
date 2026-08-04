import os
import csv
from gurobi_pulp_compat import *

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, '..', 'data')

    # Load candidate data
    candidates = []
    with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            candidates.append({
                'name': row['Candidate'].strip(),
                'salary': int(row['Salary'].strip()),
                'qualification': row['Qualification'].strip(),
                'experience': int(row['Work_Experience'].strip())
            })

    # Load general parameters
    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name'].strip()] = float(row['Value'].strip())

    max_employees = int(params['max_employees'])
    budget_limit = params['budget_limit']
    min_advanced = int(params['min_advanced_degree_candidates'])
    min_experience = params['min_work_experience']
    max_equivalent = int(params['max_equivalent_candidates'])
    min_employees = int(params['min_employees'])

    # Create optimization model
    prob = LpProblem("Recruitment", LpMinimize)

    # Decision variables: binary for each candidate
    x = {}
    for c in candidates:
        x[c['name']] = LpVariable(f"x_{c['name']}", cat='Binary')

    # Objective: minimize total salary
    prob += lpSum(c['salary'] * x[c['name']] for c in candidates)

    # Constraint 1: max employees
    prob += lpSum(x[c['name']] for c in candidates) <= max_employees

    # Constraint 2: budget
    prob += lpSum(c['salary'] * x[c['name']] for c in candidates) <= budget_limit

    # Constraint 3: at least one with Master's or Doctoral degree
    advanced_candidates = [c for c in candidates if c['qualification'] in ["Master's degree", "Doctoral degree"]]
    prob += lpSum(x[c['name']] for c in advanced_candidates) >= min_advanced

    # Constraint 4: minimum total work experience
    prob += lpSum(c['experience'] * x[c['name']] for c in candidates) >= min_experience

    # Constraint 5: at most one from pair A and E
    prob += x['A'] + x['E'] <= max_equivalent

    # Constraint 6: minimum employees
    prob += lpSum(x[c['name']] for c in candidates) >= min_employees

    # Solve
    prob.solve(GUROBI_CMD(msg=0))

    obj_val = value(prob.objective)

    for c in candidates:
        if value(x[c['name']]) > 0.5:
            print(f"Selected: {c['name']} (Salary: {c['salary']})")

    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == '__main__':
    main()