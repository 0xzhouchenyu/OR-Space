import os
import pandas as pd
from gurobi_pulp_compat import LpProblem, LpMinimize, LpVariable, LpInteger, LpStatus, GUROBI_CMD, lpSum, value

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, '..', 'data')

    cand_df = pd.read_csv(os.path.join(data_dir, 'table_1.csv'))
    cand_df.columns = [c.strip() for c in cand_df.columns]
    cand_df['Candidate'] = cand_df['Candidate'].astype(str).str.strip()

    param_df = pd.read_csv(os.path.join(data_dir, 'general_parameters.csv'))
    param_df['Parameter_Name'] = param_df['Parameter_Name'].astype(str).str.strip()
    params = {r['Parameter_Name']: float(r['Value']) for _, r in param_df.iterrows()}

    names = cand_df['Candidate'].tolist()
    salary = {r['Candidate']: float(r['Salary']) for _, r in cand_df.iterrows()}
    skill = {r['Candidate']: float(r['Skill_Level']) for _, r in cand_df.iterrows()}
    pm = {r['Candidate']: float(r['Project_Management_Experience']) for _, r in cand_df.iterrows()}

    budget = params['company_budget']
    max_emp = int(params['max_employees'])
    min_skill = params['min_skill_level']
    min_pm = params['min_project_experience']
    max_gj = int(params['max_one_candidate_g_j'])
    lead_prem = params['lead_premium']
    min_leads = int(params['min_leads'])
    mentor_bonus = params['mentor_bonus']
    max_pairs = int(params['max_pairs'])

    prob = LpProblem('HiringWithRoles', LpMinimize)
    x = {c: LpVariable(f'x_{c}', cat='Binary') for c in names}
    lead = {c: LpVariable(f'lead_{c}', cat='Binary') for c in names}
    eng = {c: LpVariable(f'eng_{c}', cat='Binary') for c in names}
    p = LpVariable('pairs', lowBound=0, upBound=max_pairs, cat=LpInteger)

    # Objective
    prob += (lpSum(salary[c]*x[c] for c in names)
             + lead_prem * lpSum(lead[c] for c in names)
             - mentor_bonus * p), 'NetCost'

    # Role exclusivity
    for c in names:
        prob += lead[c] + eng[c] == x[c], f'Role_{c}'

    # Headcount
    prob += lpSum(x[c] for c in names) <= max_emp, 'MaxEmployees'
    # Skill
    prob += lpSum(skill[c]*x[c] for c in names) >= min_skill, 'MinSkill'
    # PM experience
    prob += lpSum(pm[c]*x[c] for c in names) >= min_pm, 'MinPM'
    # G/J restriction
    prob += x['G'] + x['J'] <= max_gj, 'MaxOneGJ'
    # Min leads
    prob += lpSum(lead[c] for c in names) >= min_leads, 'MinLeads'
    # Pair capacity
    prob += p <= lpSum(lead[c] for c in names), 'PairLeadCap'
    prob += p <= lpSum(eng[c] for c in names), 'PairEngCap'
    # Budget on net cost
    prob += (lpSum(salary[c]*x[c] for c in names)
             + lead_prem * lpSum(lead[c] for c in names)
             - mentor_bonus * p) <= budget, 'Budget'

    prob.solve(GUROBI_CMD(msg=0))
    print(f'Status: {LpStatus[prob.status]}')
    for c in names:
        if x[c].varValue and x[c].varValue > 0.5:
            role = 'Lead' if lead[c].varValue > 0.5 else 'Engineer'
            print(f'Hire {c} as {role}: Salary={salary[c]}, Skill={skill[c]}, PM={pm[c]}')
    print(f'Pairs counted: {int(round(p.varValue))}')
    obj_val = value(prob.objective)
    print(f'OBJECTIVE_VALUE: {obj_val}')

if __name__ == '__main__':
    main()