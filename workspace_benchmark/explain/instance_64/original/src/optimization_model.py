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
                'skill': int(row['Skill_Level'].strip()),
                'pm_exp': int(row['Project_Management_Experience'].strip())
            })
    
    # Load general parameters
    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name'].strip()] = float(row['Value'].strip())
    
    budget = params['company_budget']
    max_employees = int(params['max_employees'])
    min_skill = params['min_skill_level']
    min_pm_exp = params['min_project_experience']
    max_gj = int(params['max_one_candidate_g_j'])
    
    # Create optimization model
    prob = LpProblem("HiringOptimization", LpMinimize)
    
    # Decision variables: binary for each candidate
    x = {}
    for c in candidates:
        x[c['name']] = LpVariable(f"x_{c['name']}", cat='Binary')
    
    # Objective: minimize total salary
    prob += lpSum(c['salary'] * x[c['name']] for c in candidates), "TotalSalary"
    
    # Budget constraint
    prob += lpSum(c['salary'] * x[c['name']] for c in candidates) <= budget, "Budget"
    
    # Max employees constraint
    prob += lpSum(x[c['name']] for c in candidates) <= max_employees, "MaxEmployees"
    
    # Min skill level constraint
    prob += lpSum(c['skill'] * x[c['name']] for c in candidates) >= min_skill, "MinSkill"
    
    # Min project management experience constraint
    prob += lpSum(c['pm_exp'] * x[c['name']] for c in candidates) >= min_pm_exp, "MinPMExp"
    
    # At most one of G and J can be hired
    prob += x['G'] + x['J'] <= max_gj, "MaxOneGJ"
    
    # Solve
    prob.solve(GUROBI_CMD(msg=0))
    
    # Print results
    print(f"Status: {LpStatus[prob.status]}")
    for c in candidates:
        if x[c['name']].varValue > 0.5:
            print(f"Hire {c['name']}: Salary={c['salary']}, Skill={c['skill']}, PM_Exp={c['pm_exp']}")
    
    obj_val = value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()