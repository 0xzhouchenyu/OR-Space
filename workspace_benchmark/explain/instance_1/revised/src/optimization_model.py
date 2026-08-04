import os
import csv
from gurobi_pulp_compat import *

def load_parameters():
    params = {}
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'general_parameters.csv')
    with open(path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name']] = float(row['Value'])
    return params

def load_demand():
    demand = {}
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'table_1.csv')
    with open(path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            demand[int(row['Week'])] = {'I': float(row['I']), 'II': float(row['II'])}
    return demand

params = load_parameters()
demand = load_demand()

T = 8
weeks = range(1, T + 1)

S0 = params['skilled_worker_count']
rate_I = params['food_I_production_rate']
rate_II = params['food_II_production_rate']
normal_hours = params['worker_weekly_hours']
overtime_hours = params['skilled_worker_overtime_hours']
train_cap = params['training_capacity']
train_period = int(params['training_period'])
wage_skilled = params['skilled_worker_weekly_wage']
wage_trainee_during = params['trainee_weekly_wage_during_training']
wage_trainee_after = params['trainee_weekly_wage_after_training']
wage_overtime = params['skilled_worker_overtime_wage']
comp_I = params['compensation_fee_food_I']
comp_II = params['compensation_fee_food_II']
new_worker_goal = params['new_worker_training_goal']

prob = LpProblem("factory_training", LpMinimize)

n_train = {}
for t in weeks:
    if t <= T - 1:
        n_train[t] = LpVariable(f"n_train_{t}", lowBound=0, cat='Integer')

h_I_s = {t: LpVariable(f"hIs_{t}", lowBound=0) for t in weeks}
h_II_s = {t: LpVariable(f"hIIs_{t}", lowBound=0) for t in weeks}
h_I_ot = {t: LpVariable(f"hIot_{t}", lowBound=0) for t in weeks}
h_II_ot = {t: LpVariable(f"hIIot_{t}", lowBound=0) for t in weeks}
h_I_g = {t: LpVariable(f"hIg_{t}", lowBound=0) for t in weeks}
h_II_g = {t: LpVariable(f"hIIg_{t}", lowBound=0) for t in weeks}
n_overtime = {t: LpVariable(f"n_ot_{t}", lowBound=0, cat='Integer') for t in weeks}
backlog_I = {t: LpVariable(f"bI_{t}", lowBound=0) for t in weeks}
backlog_II = {t: LpVariable(f"bII_{t}", lowBound=0) for t in weeks}

produce_I_flag = {t: LpVariable(f"prod_I_flag_{t}", cat='Binary') for t in weeks}

def trainers_busy(t):
    expr = 0
    for s in n_train:
        if s <= t <= s + train_period - 1:
            expr += n_train[s]
    return expr

def graduates_available(t):
    expr = 0
    for s in n_train:
        if s + train_period <= t:
            expr += train_cap * n_train[s]
    return expr

# Big-M for hours: max possible total hours in a week
BIG_M = (S0 * overtime_hours) + (S0 * train_cap * normal_hours) + 10000

for t in weeks:
    busy_t = trainers_busy(t)
    avail_skilled_t = S0 - busy_t
    grads_t = graduates_available(t)

    prob += n_overtime[t] <= avail_skilled_t, f"ot_limit_{t}"
    prob += h_I_s[t] + h_II_s[t] <= (avail_skilled_t - n_overtime[t]) * normal_hours, f"skilled_normal_hours_{t}"
    prob += h_I_ot[t] + h_II_ot[t] <= n_overtime[t] * overtime_hours, f"skilled_ot_hours_{t}"
    prob += h_I_g[t] + h_II_g[t] <= grads_t * normal_hours, f"grad_hours_{t}"

    prob += (h_I_s[t] + h_I_ot[t] + h_I_g[t]) <= BIG_M * produce_I_flag[t], f"mut_excl_I_{t}"
    prob += (h_II_s[t] + h_II_ot[t] + h_II_g[t]) <= BIG_M * (1 - produce_I_flag[t]), f"mut_excl_II_{t}"

    prod_I_t = (h_I_s[t] + h_I_ot[t] + h_I_g[t]) * rate_I
    prod_II_t = (h_II_s[t] + h_II_ot[t] + h_II_g[t]) * rate_II

    prev_bI = backlog_I[t-1] if t > 1 else 0
    prev_bII = backlog_II[t-1] if t > 1 else 0

    prob += backlog_I[t] >= prev_bI + demand[t]['I'] - prod_I_t, f"backlog_I_{t}"
    prob += backlog_II[t] >= prev_bII + demand[t]['II'] - prod_II_t, f"backlog_II_{t}"

for t in weeks:
    busy_t = trainers_busy(t)
    prob += S0 - busy_t >= 0, f"enough_skilled_{t}"

total_trained_by_8 = 0
for s in n_train:
    if s + train_period - 1 <= T:
        total_trained_by_8 += train_cap * n_train[s]

prob += total_trained_by_8 >= new_worker_goal, f"training_goal"

total_cost = 0
for t in weeks:
    busy_t = trainers_busy(t)
    avail_skilled_t = S0 - busy_t
    grads_t = graduates_available(t)

    trainees_in_training = 0
    for s in n_train:
        if s <= t <= s + train_period - 1:
            trainees_in_training += train_cap * n_train[s]

    skilled_normal_cost = (avail_skilled_t - n_overtime[t]) * wage_skilled
    skilled_overtime_cost = n_overtime[t] * wage_overtime
    trainer_cost = busy_t * wage_skilled

    trainee_training_cost = trainees_in_training * wage_trainee_during
    graduate_cost = grads_t * wage_trainee_after

    comp_cost = comp_I * backlog_I[t] + comp_II * backlog_II[t]

    total_cost += skilled_normal_cost + skilled_overtime_cost + trainer_cost
    total_cost += trainee_training_cost + graduate_cost
    total_cost += comp_cost

prob += total_cost
prob.solve(GUROBI_CMD(msg=0))

print(f"OBJECTIVE_VALUE: {value(prob.objective)}")
