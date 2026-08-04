import os
import sys
from gurobi_pulp_compat import *

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import load_general_parameters, load_task_methods

# Load data
params = load_general_parameters()
task_methods = load_task_methods()

# Extract core parameters
skilled_wage = params['skilled_worker_weekly_wage']
laborer_wage = params['laborer_weekly_wage']
skilled_hours = params['skilled_worker_weekly_hours']
laborer_hours = params['laborer_weekly_hours']
max_skilled = params['max_skilled_workers']
max_laborers = params['max_laborers']
min_skilled_task3_B = params['min_skilled_workers_task3_methodB']
skilled_hiring_ratio = params['skilled_worker_hiring_ratio']

# Task-level skilled share bounds
min_share = {
    'Task_1': params['min_skilled_share_task1'],
    'Task_2': params['min_skilled_share_task2'],
    'Task_3': params['min_skilled_share_task3']
}
max_share = {
    'Task_1': params['max_skilled_share_task1'],
    'Task_2': params['max_skilled_share_task2'],
    'Task_3': params['max_skilled_share_task3']
}

# Organize task-method data
tasks = ['Task_1', 'Task_2', 'Task_3']
methods = ['Method_A', 'Method_B']

# Build dictionary: (task, method) -> {Effective_Hours, Fixed_Cost}
tm_data = {}
for row in task_methods:
    key = (row['Task'], row['Method'])
    tm_data[key] = row

# Create the problem
prob = LpProblem("WorkerAllocation_TaskSkillMix", LpMinimize)

# Decision variables
# Method selection
y = {(t, m): LpVariable(f"y_{t}_{m}", cat='Binary') for t in tasks for m in methods}

# Method-level skilled and laborers
s = {(t, m): LpVariable(f"s_{t}_{m}", lowBound=0) for t in tasks for m in methods}
l = {(t, m): LpVariable(f"l_{t}_{m}", lowBound=0) for t in tasks for m in methods}

# Total skilled and laborers
total_skilled = LpVariable("total_skilled", lowBound=0)
total_laborers = LpVariable("total_laborers", lowBound=0)

# NEW: Task-level total skilled and laborers
S_task = {t: LpVariable(f"S_{t}", lowBound=0) for t in tasks}
L_task = {t: LpVariable(f"L_{t}", lowBound=0) for t in tasks}

# Objective: minimize wage cost + fixed method costs
prob += (
    skilled_wage * total_skilled
    + laborer_wage * total_laborers
    + lpSum(tm_data[t, m]['Fixed_Cost'] * y[t, m] for t in tasks for m in methods)
), "TotalWeeklyCost"

# Aggregate definitions
prob += total_skilled == lpSum(s[t, m] for t in tasks for m in methods), "TotalSkilledDef"
prob += total_laborers == lpSum(l[t, m] for t in tasks for m in methods), "TotalLaborersDef"

# Link task-level and method-level allocations
for t in tasks:
    prob += S_task[t] == lpSum(s[t, m] for m in methods), f"TaskSkilledSum_{t}"
    prob += L_task[t] == lpSum(l[t, m] for m in methods), f"TaskLaborerSum_{t}"

# Exactly one method per task
for t in tasks:
    prob += lpSum(y[t, m] for m in methods) == 1, f"OneMethod_{t}"

# Hours requirements and linking constraints
M_big = 10000
for t in tasks:
    for m in methods:
        req_hours = tm_data[t, m]['Effective_Hours']
        # Hours constraint
        prob += (
            skilled_hours * s[t, m] + laborer_hours * l[t, m]
            >= req_hours * y[t, m]
        ), f"Hours_{t}_{m}"
        # Linking: if method not chosen, workers cannot be assigned
        prob += s[t, m] <= M_big * y[t, m], f"LinkS_{t}_{m}"
        prob += l[t, m] <= M_big * y[t, m], f"LinkL_{t}_{m}"

# Capacity constraints on total workers
prob += total_skilled <= max_skilled, "MaxSkilled"
prob += total_laborers <= max_laborers, "MaxLaborers"

# Global skilled-to-laborer hiring ratio
prob += total_skilled <= skilled_hiring_ratio * total_laborers, "SkilledRatioGlobal"

# Exclusion rule: Task_1 Method_B excludes Task_3 Method_A
prob += y['Task_1', 'Method_B'] + y['Task_3', 'Method_A'] <= 1, "ExclusionRule_T1B_T3A"

# Minimum skilled workers for Task_3 if Method_B is chosen
prob += s['Task_3', 'Method_B'] >= min_skilled_task3_B * y['Task_3', 'Method_B'], "MinSkilledTask3B"

# NEW: Task-level skill mix constraints
for t in tasks:
    # S_t >= min_share[t] * (S_t + L_t)
    prob += S_task[t] >= min_share[t] * (S_task[t] + L_task[t]), f"MinShare_{t}"
    # S_t <= max_share[t] * (S_t + L_t)
    prob += S_task[t] <= max_share[t] * (S_task[t] + L_task[t]), f"MaxShare_{t}"

# Solve the MILP
prob.solve(GUROBI_CMD(msg=0))

# Retrieve objective value
obj_val = value(prob.objective)

print(f"OBJECTIVE_VALUE: {obj_val}")
