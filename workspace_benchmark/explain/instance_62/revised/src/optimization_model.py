import os
import pandas as pd
import gurobi_pulp_compat as pulp

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, '..', 'data')

    restaurants_df = pd.read_csv(os.path.join(data_dir, 'table_1.csv'))
    params_df = pd.read_csv(os.path.join(data_dir, 'general_parameters.csv'))
    params = {row['Parameter_Name'].strip(): float(row['Value']) for _, row in params_df.iterrows()}

    budget = params['investment_budget']
    uplift = params['premium_revenue_uplift']
    upgrade_cost = params['premium_upgrade_cost']
    staff_cap = params['staff_hours_cap']

    rests = []
    for _, row in restaurants_df.iterrows():
        rests.append({
            'name': row['Restaurant'].strip(),
            'revenue': float(row['Annual_Revenue']),
            'cost': float(row['Cost']),
            'std_h': float(row['Standard_Staff_Hours']),
            'prem_h': float(row['Premium_Staff_Hours']),
        })

    prob = pulp.LpProblem("Restaurant_Investment_Modes", pulp.LpMaximize)
    x = {r['name']: pulp.LpVariable(f"x_{r['name']}", cat='Binary') for r in rests}
    p = {r['name']: pulp.LpVariable(f"p_{r['name']}", cat='Binary') for r in rests}

    # Objective
    prob += pulp.lpSum(r['revenue'] * (x[r['name']] + uplift * p[r['name']]) for r in rests)

    # Mode coupling
    for r in rests:
        prob += p[r['name']] <= x[r['name']], f"Mode_Coupling_{r['name']}"

    # Combined budget
    prob += pulp.lpSum(r['cost'] * x[r['name']] + upgrade_cost * p[r['name']] for r in rests) <= budget, "Budget"

    # Staff hours
    prob += pulp.lpSum(r['std_h'] * (x[r['name']] - p[r['name']]) + r['prem_h'] * p[r['name']] for r in rests) <= staff_cap, "Staff_Hours"

    # Mutual exclusion D-A
    prob += x['Restaurant_D'] + x['Restaurant_A'] <= 1, "D_A_Exclusion"

    prob.solve(pulp.GUROBI_CMD(msg=0))
    value = pulp.value(prob.objective)
    print(f"OBJECTIVE_VALUE: {value}")

if __name__ == "__main__":
    main()