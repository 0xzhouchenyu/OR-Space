import os
import csv
from gurobi_pulp_compat import LpProblem, LpMinimize, LpVariable, lpSum, value, GUROBI_CMD

def main():
    # Set up data directory
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

    # Read general parameters
    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['Parameter_Name'].strip()
            val = row['Value'].strip()
            params[name] = val

    # Extract relevant parameters
    max_children = int(params['max_children_trip'])
    min_children = int(params['min_children_trip'])
    max_distinct_children_trip = int(params['max_distinct_children_trip'])
    total_cost_budget = float(params['total_cost_budget'])
    bonus_saving = float(params['bonus_saving'])
    min_bob_days = int(params['min_bob_days'])

    # Read table_1 for children and costs
    children = []
    costs = {}
    with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['Child'].strip()
            cost = float(row['Cost'].strip())
            children.append(name)
            costs[name] = cost

    days = [1, 2]

    # Create the optimization model
    prob = LpProblem("FamilyTwoDayTrip", LpMinimize)

    # Decision variables
    # x[child, day] = 1 if child attends on that day
    x = {(c, d): LpVariable(f"x_{c}_day{d}", cat='Binary') for c in children for d in days}

    # y[child] = 1 if child attends on both days
    y = {c: LpVariable(f"y_{c}", cat='Binary') for c in children}

    # z[child] = 1 if child attends on at least one day
    z = {c: LpVariable(f"z_{c}", cat='Binary') for c in children}

    # Objective: minimize total two-day cost minus savings
    prob += (
        lpSum(costs[c] * x[(c, 1)] for c in children) +
        lpSum(costs[c] * x[(c, 2)] for c in children) -
        bonus_saving * lpSum(y[c] for c in children)
    ), "TotalNetCost"

    # Per-day min and max children constraints
    for d in days:
        prob += lpSum(x[(c, d)] for c in children) >= min_children, f"MinChildren_day{d}"
        prob += lpSum(x[(c, d)] for c in children) <= max_children, f"MaxChildren_day{d}"

    # Distinct children logic and limit
    for c in children:
        prob += z[c] >= x[(c, 1)], f"Z_ge_X1_{c}"
        prob += z[c] >= x[(c, 2)], f"Z_ge_X2_{c}"
        prob += z[c] <= x[(c, 1)] + x[(c, 2)], f"Z_le_sumX_{c}"
    prob += lpSum(z[c] for c in children) <= max_distinct_children_trip, "MaxDistinctChildren"

    # Bob must attend at least min_bob_days days
    prob += x[("Bob", 1)] + x[("Bob", 2)] >= min_bob_days, "BobMinDays"

    # Day-specific relationship constraints
    for d in days:
        # Alice and Diana cannot both be taken on the same day
        prob += x[("Alice", d)] + x[("Diana", d)] <= 1, f"AliceDianaConflict_day{d}"

        # Bob and Charlie cannot both be taken on the same day
        prob += x[("Bob", d)] + x[("Charlie", d)] <= 1, f"BobCharlieConflict_day{d}"

        # Charlie must be accompanied by Diana
        prob += x[("Charlie", d)] <= x[("Diana", d)], f"CharlieRequiresDiana_day{d}"

        # Diana must be accompanied by Ella
        prob += x[("Diana", d)] <= x[("Ella", d)], f"DianaRequiresElla_day{d}"

    # Availability constraints
    # Charlie only day 2
    prob += x[("Charlie", 1)] == 0, "CharlieNotDay1"
    # Diana only day 2
    prob += x[("Diana", 1)] == 0, "DianaNotDay1"
    # Alice only day 1
    prob += x[("Alice", 2)] == 0, "AliceNotDay2"

    # Two-day participation logic for y[c]
    for c in children:
        prob += y[c] <= x[(c, 1)], f"Y_le_X1_{c}"
        prob += y[c] <= x[(c, 2)], f"Y_le_X2_{c}"
        prob += y[c] >= x[(c, 1)] + x[(c, 2)] - 1, f"Y_ge_sumXminus1_{c}"

    # Total cost budget constraint
    total_cost_expr = (
        lpSum(costs[c] * x[(c, 1)] for c in children) +
        lpSum(costs[c] * x[(c, 2)] for c in children) -
        bonus_saving * lpSum(y[c] for c in children)
    )
    prob += total_cost_expr <= total_cost_budget, "TotalCostBudget"

    # Solve
    prob.solve(GUROBI_CMD(msg=0))

    obj_val = value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()
