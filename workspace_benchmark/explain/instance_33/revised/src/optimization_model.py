import os
import csv
from gurobi_pulp_compat import *

# Load data directory
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# Read items and values
items = []
values = []
with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        items.append(row['Item'].strip())
        values.append(int(row['Value'].strip()))

n = len(items)

# Read general parameters
params = {}
with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        name = row['Parameter_Name'].strip()
        val = row['Value'].strip()
        if val != '':
            try:
                params[name] = float(val)
            except ValueError:
                params[name] = val

son1_min_share = float(params.get('son1_min_share', 0.5))
high_value_threshold = float(params.get('high_value_threshold', 15000.0))
max_high_value_items_per_son = int(float(params.get('max_high_value_items_per_son', 3)))
deferred_diamonds_per_son = int(float(params.get('deferred_diamonds_per_son', 1)))
immediate_tax_weight = float(params.get('immediate_tax_weight', 1.0))
total_tax_weight = float(params.get('total_tax_weight', 0.2))

# Compute total value
total_value = sum(values)

# Identify sets
high_value_indices = [i for i, v in enumerate(values) if v > high_value_threshold]
diamond_indices = [i for i, item in enumerate(items) if 'Diamond' in item]
jack_russell_indices = [i for i, item in enumerate(items) if 'Jack Russell' in item]

# Create optimization model
model = LpProblem("Inheritance_Split_Restructured", LpMinimize)

# Decision variables
x_immediate_s1 = [LpVariable(f"x_immediate_s1_{i}", cat='Binary') for i in range(n)]
x_immediate_s2 = [LpVariable(f"x_immediate_s2_{i}", cat='Binary') for i in range(n)]
x_deferred = [LpVariable(f"x_deferred_{i}", cat='Binary') for i in range(n)]

x_owner_s1 = [LpVariable(f"x_owner_s1_{i}", cat='Binary') for i in range(n)]
x_owner_s2 = [LpVariable(f"x_owner_s2_{i}", cat='Binary') for i in range(n)]

# Auxiliary variables for deferred diamonds per son
y_deferred_s1 = [LpVariable(f"y_deferred_s1_{i}", cat='Binary') for i in range(n)]
y_deferred_s2 = [LpVariable(f"y_deferred_s2_{i}", cat='Binary') for i in range(n)]

# Difference variables
diff_immediate = LpVariable("diff_immediate", lowBound=0)
diff_total = LpVariable("diff_total", lowBound=0)

# Objective variable
tax_weighted_diff = LpVariable("tax_weighted_diff", lowBound=0)

# 1) Ownership: each item belongs to exactly one son
for i in range(n):
    model += x_owner_s1[i] + x_owner_s2[i] == 1, f"ownership_one_son_{i}"

# 2) Immediate vs deferred split and consistency
for i in range(n):
    # immediate or deferred
    model += x_immediate_s1[i] + x_immediate_s2[i] + x_deferred[i] == 1, f"immediate_or_deferred_{i}"
    # immediate implies ownership
    model += x_immediate_s1[i] <= x_owner_s1[i], f"immediate_s1_own_{i}"
    model += x_immediate_s2[i] <= x_owner_s2[i], f"immediate_s2_own_{i}"

# 3) Jack Russell dogs must not be separated in any dimension
if len(jack_russell_indices) == 2:
    j1, j2 = jack_russell_indices
    # Immediate assignments identical
    model += x_immediate_s1[j1] == x_immediate_s1[j2], "jr_immediate_s1"
    model += x_immediate_s2[j1] == x_immediate_s2[j2], "jr_immediate_s2"
    # Deferred status identical
    model += x_deferred[j1] == x_deferred[j2], "jr_deferred"
    # Ownership identical
    model += x_owner_s1[j1] == x_owner_s1[j2], "jr_owner_s1"
    model += x_owner_s2[j1] == x_owner_s2[j2], "jr_owner_s2"

# 4) High-value item limit per son
if high_value_indices:
    model += lpSum(x_owner_s1[i] for i in high_value_indices) <= max_high_value_items_per_son, "high_value_limit_s1"
    model += lpSum(x_owner_s2[i] for i in high_value_indices) <= max_high_value_items_per_son, "high_value_limit_s2"

# 5) Deferred diamonds per son using auxiliary variables
for i in range(n):
    if i in diamond_indices:
        # y_deferred_s1[i] is 1 iff deferred and owned by s1
        model += y_deferred_s1[i] <= x_deferred[i], f"y_s1_deferred_leq_deferred_{i}"
        model += y_deferred_s1[i] <= x_owner_s1[i], f"y_s1_deferred_leq_own_{i}"
        model += y_deferred_s1[i] >= x_deferred[i] + x_owner_s1[i] - 1, f"y_s1_deferred_geq_sum_{i}"
        # y_deferred_s2[i] is 1 iff deferred and owned by s2
        model += y_deferred_s2[i] <= x_deferred[i], f"y_s2_deferred_leq_deferred_{i}"
        model += y_deferred_s2[i] <= x_owner_s2[i], f"y_s2_deferred_leq_own_{i}"
        model += y_deferred_s2[i] >= x_deferred[i] + x_owner_s2[i] - 1, f"y_s2_deferred_geq_sum_{i}"
    else:
        # Non-diamond items cannot contribute to deferred diamond counts
        model += y_deferred_s1[i] == 0, f"y_s1_non_diamond_zero_{i}"
        model += y_deferred_s2[i] == 0, f"y_s2_non_diamond_zero_{i}"

# Limit of deferred diamonds per son
model += lpSum(y_deferred_s1[i] for i in range(n)) <= deferred_diamonds_per_son, "deferred_diamonds_limit_s1"
model += lpSum(y_deferred_s2[i] for i in range(n)) <= deferred_diamonds_per_son, "deferred_diamonds_limit_s2"

# 6) Minimum share for son 1 in total ownership
value_total_s1 = lpSum(values[i] * x_owner_s1[i] for i in range(n))
model += value_total_s1 >= son1_min_share * total_value, "min_share_s1"

# 7) Define immediate and total values for both sons
value_immediate_s1 = lpSum(values[i] * x_immediate_s1[i] for i in range(n))
value_immediate_s2 = lpSum(values[i] * x_immediate_s2[i] for i in range(n))

value_total_s2 = lpSum(values[i] * x_owner_s2[i] for i in range(n))

# 8) Absolute difference constraints for immediate and total values
# diff_immediate >= |V_immediate_s1 - V_immediate_s2|
model += diff_immediate >= value_immediate_s1 - value_immediate_s2, "diff_immediate_pos"
model += diff_immediate >= value_immediate_s2 - value_immediate_s1, "diff_immediate_neg"

# diff_total >= |V_total_s1 - V_total_s2|
model += diff_total >= value_total_s1 - value_total_s2, "diff_total_pos"
model += diff_total >= value_total_s2 - value_total_s1, "diff_total_neg"

# 9) Tax-weighted difference definition
model += tax_weighted_diff == immediate_tax_weight * diff_immediate + total_tax_weight * diff_total, "tax_weighted_def"

# Objective: minimize tax_weighted_diff
model += tax_weighted_diff

# Solve the model
model.solve(GUROBI_CMD(msg=0))

obj_val = value(tax_weighted_diff)

# Print only the required objective value line
print(f"OBJECTIVE_VALUE: {obj_val}")
