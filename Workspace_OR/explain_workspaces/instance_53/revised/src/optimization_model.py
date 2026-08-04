import os
import csv
from gurobi_pulp_compat import *

def main():
    # Load data directory
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

    # Read costs from table_1.csv
    # Columns: Child,Cost_budget,Cost_balanced,Cost_premium
    cost_budget = {}
    cost_balanced = {}
    cost_premium = {}
    with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            child = row['Child'].strip()
            cost_budget[child] = float(row['Cost_budget'].strip())
            cost_balanced[child] = float(row['Cost_balanced'].strip())
            cost_premium[child] = float(row['Cost_premium'].strip())

    # Read general parameters
    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name'].strip()] = row['Value'].strip()

    max_children = int(params['max_children'])
    min_children = int(params['min_children'])
    fairness_penalty = float(params['fairness_penalty'])
    max_total_cost = float(params['max_total_cost'])
    min_children_per_mode = int(params['min_children_per_mode'])

    children = list(cost_budget.keys())

    # Create problem
    prob = LpProblem('ZhangFamilyTripPaceMode', LpMinimize)

    # Decision variables for children (binary)
    x = {child: LpVariable(f"x_{child}", cat='Binary') for child in children}

    # Mode selection binaries
    z_budget = LpVariable('z_budget', cat='Binary')
    z_balanced = LpVariable('z_balanced', cat='Binary')
    z_premium = LpVariable('z_premium', cat='Binary')

    # Auxiliary continuous variables for fairness spread
    max_child_cost = LpVariable('max_child_cost', lowBound=0)
    min_child_cost = LpVariable('min_child_cost', lowBound=0)

    # Auxiliary cost variables y_c for each child
    y = {child: LpVariable(f"y_{child}", lowBound=0) for child in children}

    # Precompute big-M for each child: max of its possible mode costs
    bigM = {}
    for c in children:
        bigM[c] = max(cost_budget[c], cost_balanced[c], cost_premium[c])

    # Mode-dependent cost expression per child (affine in mode binaries)
    cost_mode_expr = {}
    for c in children:
        cost_mode_expr[c] = (
            cost_budget[c] * z_budget +
            cost_balanced[c] * z_balanced +
            cost_premium[c] * z_premium
        )

    # Linearization constraints linking y_c, x_c, and cost_mode_expr[c]
    for c in children:
        M = bigM[c]
        # y_c = 0 if x_c = 0, y_c = cost_mode_expr if x_c = 1
        prob += y[c] <= M * x[c], f"y_le_Mx_{c}"
        prob += y[c] <= cost_mode_expr[c] + M * (1 - x[c]), f"y_le_costplus_{c}"
        prob += y[c] >= cost_mode_expr[c] - M * (1 - x[c]), f"y_ge_costminus_{c}"

    # Total monetary cost
    total_monetary_cost = lpSum(y[c] for c in children)

    # Objective: monetary cost + fairness penalty * (max_child_cost - min_child_cost)
    prob += total_monetary_cost + fairness_penalty * (max_child_cost - min_child_cost)

    # Ginny must go
    prob += x['Ginny'] == 1, 'Ginny_must_go'

    # At most max_children
    prob += lpSum(x[c] for c in children) <= max_children, 'Max_children'

    # At least min_children
    prob += lpSum(x[c] for c in children) >= min_children, 'Min_children'

    # Logical relationships (same as original)
    # If Harry is taken, Fred cannot be taken: x_Harry + x_Fred <= 1
    prob += x['Harry'] + x['Fred'] <= 1, 'Harry_no_Fred'

    # If Harry is taken, George cannot be taken: x_Harry + x_George <= 1
    prob += x['Harry'] + x['George'] <= 1, 'Harry_no_George'

    # If George is taken, Fred must also be taken: x_George <= x_Fred
    prob += x['George'] <= x['Fred'], 'George_requires_Fred'

    # If George is taken, Hermione must also be taken: x_George <= x_Hermione
    prob += x['George'] <= x['Hermione'], 'George_requires_Hermione'

    # Mode selection: exactly one mode
    prob += z_budget + z_balanced + z_premium == 1, 'Exactly_one_mode'

    # Mode-size coupling constraints for balanced and premium modes
    total_children = lpSum(x[c] for c in children)
    prob += total_children >= min_children_per_mode * z_balanced, 'Min_children_balanced_mode'
    prob += total_children >= min_children_per_mode * z_premium, 'Min_children_premium_mode'

    # Budget constraint on total monetary cost
    prob += total_monetary_cost <= max_total_cost, 'Budget_constraint'

    # Max/min child cost linking constraints for fairness spread (over mode-dependent per-child costs)
    for c in children:
        prob += max_child_cost >= cost_mode_expr[c], f'Max_cost_ge_{c}'
        prob += min_child_cost <= cost_mode_expr[c], f'Min_cost_le_{c}'

    # Solve with Gurobi
    prob.solve(GUROBI_CMD(msg=0))

    # Print selected mode
    selected_mode = None
    if z_budget.varValue is not None and z_budget.varValue > 0.5:
        selected_mode = 'budget'
    elif z_balanced.varValue is not None and z_balanced.varValue > 0.5:
        selected_mode = 'balanced'
    elif z_premium.varValue is not None and z_premium.varValue > 0.5:
        selected_mode = 'premium'

    if selected_mode is not None:
        print(f"Mode_selected: {selected_mode}")

    # Print selected children
    for c in children:
        if x[c].varValue is not None and x[c].varValue > 0.5:
            # Compute effective cost for reporting based on selected mode
            z_b = z_budget.varValue or 0
            z_bal = z_balanced.varValue or 0
            z_pre = z_premium.varValue or 0
            cost_val = (
                cost_budget[c] * z_b +
                cost_balanced[c] * z_bal +
                cost_premium[c] * z_pre
            )
            print(f"{c}: selected (effective_cost={cost_val})")

    obj_val = value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == '__main__':
    main()
