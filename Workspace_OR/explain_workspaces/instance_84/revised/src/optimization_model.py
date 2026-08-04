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

    min_managers = int(params['min_managers'])
    max_managers = int(params['max_managers'])
    min_manager_experience = params['min_manager_experience']
    manager_bonus_per_candidate = params['manager_bonus_per_candidate']

    # Create optimization model
    prob = LpProblem("Recruitment_Role_Based", LpMinimize)

    # Decision variables
    x = {}  # selected (any role)
    y_manager = {}
    y_specialist = {}

    for c in candidates:
        name = c['name']
        x[name] = LpVariable(f"x_{name}", cat='Binary')
        y_manager[name] = LpVariable(f"y_manager_{name}", cat='Binary')
        y_specialist[name] = LpVariable(f"y_specialist_{name}", cat='Binary')

    # Base salary cost
    base_salary_cost = lpSum(c['salary'] * x[c['name']] for c in candidates)
    # Manager bonus cost
    manager_bonus_cost = manager_bonus_per_candidate * lpSum(y_manager[c['name']] for c in candidates)

    # Objective: minimize total effective cost
    prob += base_salary_cost + manager_bonus_cost

    # Linking constraints: each candidate either manager or specialist or none
    for c in candidates:
        name = c['name']
        prob += y_manager[name] + y_specialist[name] == x[name]

    # Max and min employees (use x)
    prob += lpSum(x[c['name']] for c in candidates) <= max_employees
    prob += lpSum(x[c['name']] for c in candidates) >= min_employees

    # Budget constraint: only base salaries are limited by budget_limit
    prob += base_salary_cost <= budget_limit

    # At least one with Master's or Doctoral degree
    advanced_candidates = [c for c in candidates if c['qualification'] in ["Master's degree", "Doctoral degree"]]
    prob += lpSum(x[c['name']] for c in advanced_candidates) >= min_advanced

    # Minimum total work experience (all selected employees)
    prob += lpSum(c['experience'] * x[c['name']] for c in candidates) >= min_experience

    # Equivalent candidates: at most one of A and E
    prob += x['A'] + x['E'] <= max_equivalent

    # Role-based headcount limits
    prob += lpSum(y_manager[c['name']] for c in candidates) >= min_managers
    prob += lpSum(y_manager[c['name']] for c in candidates) <= max_managers

    # Manager experience requirement
    prob += lpSum(c['experience'] * y_manager[c['name']] for c in candidates) >= min_manager_experience

    # Solve
    prob.solve(GUROBI_CMD(msg=0))

    obj_val = value(prob.objective)

    # Print chosen candidates and roles for inspection (not required for evaluation)
    for c in candidates:
        name = c['name']
        if value(x[name]) > 0.5:
            role = "Manager" if value(y_manager[name]) > 0.5 else "Specialist"
            print(f"Selected: {name} as {role} (Salary: {c['salary']})")

    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == '__main__':
    main()
