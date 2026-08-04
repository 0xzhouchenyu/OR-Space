import os
import csv
from gurobi_pulp_compat import *

# Load data
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
total_value = sum(values)

# Create the optimization model
model = LpProblem("Inheritance_Split", LpMinimize)

# Binary variables: x[i] = 1 if item i goes to son 1, 0 if to son 2
x = [LpVariable(f"x_{i}", cat='Binary') for i in range(n)]

# Variable for the absolute difference
diff = LpVariable("diff", lowBound=0)

# Value assigned to son 1
value_son1 = lpSum(values[i] * x[i] for i in range(n))

# Constraints for absolute difference
# diff >= value_son1 - (total_value - value_son1) = 2*value_son1 - total_value
# diff >= -(2*value_son1 - total_value)
model += diff >= 2 * value_son1 - total_value
model += diff >= total_value - 2 * value_son1

# Jack Russell racing dogs must not be separated
# Find indices of the two Jack Russell dogs
jr_indices = [i for i, item in enumerate(items) if 'Jack Russell' in item]
if len(jr_indices) == 2:
    model += x[jr_indices[0]] == x[jr_indices[1]]

# Objective: minimize the difference
model += diff

# Solve
model.solve(GUROBI_CMD(msg=0))

# Print solution details
obj_val = value(diff)

print("Status:", LpStatus[model.status])
print(f"Total inheritance value: {total_value}")
print()

son1_items = []
son2_items = []
son1_val = 0
son2_val = 0
for i in range(n):
    if value(x[i]) > 0.5:
        son1_items.append((items[i], values[i]))
        son1_val += values[i]
    else:
        son2_items.append((items[i], values[i]))
        son2_val += values[i]

print("Son 1 receives:")
for item, val in son1_items:
    print(f"  {item}: {val}")
print(f"  Total: {son1_val}")
print()
print("Son 2 receives:")
for item, val in son2_items:
    print(f"  {item}: {val}")
print(f"  Total: {son2_val}")
print()
print(f"Difference: {abs(son1_val - son2_val)}")

print(f"OBJECTIVE_VALUE: {obj_val}")