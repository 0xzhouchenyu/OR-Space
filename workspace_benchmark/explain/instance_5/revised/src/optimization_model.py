import gurobi_pulp_compat as pulp
import pandas as pd
import os


def solve():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    table_1_path = os.path.join(base_dir, '..', 'data', 'table_1.csv')
    params_path = os.path.join(base_dir, '..', 'data', 'general_parameters.csv')

    df = pd.read_csv(table_1_path)
    params = pd.read_csv(params_path)

    def get_param(name, default=None):
        row = params[params['Parameter_Name'] == name]
        if row.empty:
            if default is None:
                raise ValueError(f"Missing parameter: {name}")
            return default
        return float(row['Value'].iloc[0])

    budget = get_param('budget')
    food_intake = get_param('food_intake')
    weekday_budget_share = get_param('weekday_budget_share')
    max_prep_time_weekday = get_param('max_prep_time_weekday')
    max_prep_time_weekend = get_param('max_prep_time_weekend')
    weekend_protein_ban = int(get_param('weekend_protein_ban'))
    veg_balance_penalty = get_param('veg_balance_penalty')

    # Handle missing fiber content as 0 (for proteins)
    df['Fiber_Content_per_100g'] = df['Fiber_Content_per_100g'].fillna(0.0)

    foods = df['Food'].tolist()
    types = df.set_index('Food')['Type'].to_dict()
    fiber = df.set_index('Food')['Fiber_Content_per_100g'].to_dict()
    price = df.set_index('Food')['Price_per_100g'].to_dict()
    prep_time = df.set_index('Food')['prep_time_per_100g'].to_dict()

    proteins = [f for f in foods if types[f] == 'protein']
    vegetables = [f for f in foods if types[f] == 'vegetable']

    scenarios = ['weekday', 'weekend']

    # Problem definition
    prob = pulp.LpProblem("Two_Scenario_Maximize_Fiber_With_Balance", pulp.LpMaximize)

    # Decision variables
    x = {(s, f): pulp.LpVariable(f"x_{s}_{f}", lowBound=0, cat='Continuous')
         for s in scenarios for f in foods}
    y = {(s, f): pulp.LpVariable(f"y_{s}_{f}", cat='Binary')
         for s in scenarios for f in foods}
    z = {p: pulp.LpVariable(f"z_{p}", cat='Binary') for p in proteins}
    d = {v: pulp.LpVariable(f"d_{v}", lowBound=0, cat='Continuous') for v in vegetables}

    # Objective: sum fiber over both scenarios minus veg balance penalty
    prob += (
        pulp.lpSum(fiber[f] * x[(s, f)] for s in scenarios for f in foods)
        - veg_balance_penalty * pulp.lpSum(d[v] for v in vegetables)
    )

    # Common M for linking
    M_intake = food_intake / 100.0

    # 1. Total food intake per scenario
    for s in scenarios:
        prob += pulp.lpSum(x[(s, f)] for f in foods) == M_intake, f"total_intake_{s}"

    # 2. Budget constraints
    weekday_budget = weekday_budget_share * budget
    weekend_budget = (1.0 - weekday_budget_share) * budget

    prob += (
        pulp.lpSum(price[f] * x[('weekday', f)] for f in foods)
        <= weekday_budget
    ), "weekday_budget"

    prob += (
        pulp.lpSum(price[f] * x[('weekend', f)] for f in foods)
        <= weekend_budget
    ), "weekend_budget"

    prob += (
        pulp.lpSum(price[f] * x[(s, f)] for s in scenarios for f in foods)
        <= budget
    ), "total_budget"

    # 3. Exactly one active protein overall
    if proteins:
        prob += pulp.lpSum(z[p] for p in proteins) == 1, "one_protein_activation"
    # Back-link: an activated protein must actually appear in at least one scenario
    if proteins:
        for p in proteins:
            prob += z[p] <= y[('weekday', p)] + y[('weekend', p)], f"backlink_z_{p}"


    # 4. Scenario-specific protein usage and weekend protein ban
    for s in scenarios:
        for p in proteins:
            prob += y[(s, p)] <= z[p], f"link_yz_{s}_{p}"

    if weekend_protein_ban == 1:
        for p in proteins:
            # Force y[weekend,p] = 0
            prob += y[('weekend', p)] <= 0, f"ban_weekend_protein_{p}"

    # 5. At least two vegetables per scenario
    for s in scenarios:
        prob += pulp.lpSum(y[(s, v)] for v in vegetables) >= 2, f"min_two_veg_{s}"

    # 6. Linking x and y
    for s in scenarios:
        for f in foods:
            prob += x[(s, f)] >= 0.1 * y[(s, f)], f"min_inclusion_{s}_{f}"
            prob += x[(s, f)] <= M_intake * y[(s, f)], f"max_inclusion_{s}_{f}"

    # 7. Preparation time constraints
    prob += (
        pulp.lpSum(prep_time[f] * x[('weekday', f)] for f in foods)
        <= max_prep_time_weekday
    ), "prep_time_weekday"

    prob += (
        pulp.lpSum(prep_time[f] * x[('weekend', f)] for f in foods)
        <= max_prep_time_weekend
    ), "prep_time_weekend"

    # 8. Vegetable balance constraints using deviation variables d[v]
    for v in vegetables:
        x_weekday_v = x[('weekday', v)]
        x_weekend_v = x[('weekend', v)]
        prob += d[v] >= x_weekday_v - x_weekend_v, f"dev_pos_{v}"
        prob += d[v] >= x_weekend_v - x_weekday_v, f"dev_neg_{v}"

    # Solve
    prob.solve(pulp.GUROBI_CMD(msg=False))

    obj_val = pulp.value(prob.objective)
    return round(obj_val, 4)


if __name__ == '__main__':
    value = solve()
    print(f"OBJECTIVE_VALUE: {value}")
