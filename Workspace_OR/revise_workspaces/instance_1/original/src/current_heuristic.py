import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import load_parameters, load_demand
from gurobi_pulp_compat import *

params = load_parameters()
demand = load_demand()

T = 8  # weeks
weeks = range(1, T + 1)

# Parameters
S0 = params['skilled_worker_count']  # 50
rate_I = params['food_I_production_rate']  # 10 kg/h
rate_II = params['food_II_production_rate']  # 6 kg/h
normal_hours = params['worker_weekly_hours']  # 40
overtime_hours = params['skilled_worker_overtime_hours']  # 60
train_cap = params['training_capacity']  # 3 trainees per trainer
train_period = params['training_period']  # 2 weeks
wage_skilled = params['skilled_worker_weekly_wage']  # 360
wage_trainee_during = params['trainee_weekly_wage_during_training']  # 120
wage_trainee_after = params['trainee_weekly_wage_after_training']  # 240
wage_overtime = params['skilled_worker_overtime_wage']  # 540
comp_I = params['compensation_fee_food_I']  # 0.5
comp_II = params['compensation_fee_food_II']  # 0.6
new_worker_goal = params['new_worker_training_goal']  # 50

prob = LpProblem("factory_training", LpMinimize)

# Decision variables
# n_train[t] = number of skilled workers assigned to training starting in week t
# Training takes 2 weeks, so a trainer starting in week t is busy in weeks t and t+1
# Each trainer trains 3 new workers who become available in week t+2
n_train = {}
for t in weeks:
    if t <= T - 1:  # Can start training in weeks 1..7 (need 2 weeks)
        n_train[t] = LpVariable(f"n_train_{t}", lowBound=0, cat='Integer')

# Hours allocated to food I and II by skilled workers (normal and overtime)
# and by graduated trainees
# Let's think about worker availability each week

# Graduated trainees available in week t: those who started training in week t-2 or earlier
# Trainees who start training in week s finish after week s+1, available from week s+2

# h_I_skilled[t] = hours skilled workers spend on food I in week t (normal time)
# h_II_skilled[t] = hours skilled workers spend on food II in week t (normal time)
# h_I_overtime[t] = overtime hours on food I
# h_II_overtime[t] = overtime hours on food II
# Similarly for graduated trainees (they work normal hours at trainee_after wage)

h_I_s = {t: LpVariable(f"hIs_{t}", lowBound=0) for t in weeks}
h_II_s = {t: LpVariable(f"hIIs_{t}", lowBound=0) for t in weeks}
h_I_ot = {t: LpVariable(f"hIot_{t}", lowBound=0) for t in weeks}
h_II_ot = {t: LpVariable(f"hIIot_{t}", lowBound=0) for t in weeks}

# Graduated trainees hours
h_I_g = {t: LpVariable(f"hIg_{t}", lowBound=0) for t in weeks}
h_II_g = {t: LpVariable(f"hIIg_{t}", lowBound=0) for t in weeks}

# Number of skilled workers doing overtime in week t
n_overtime = {t: LpVariable(f"n_ot_{t}", lowBound=0, cat='Integer') for t in weeks}

# Delayed delivery (backlog) for food I and II
# backlog[t] = cumulative unmet demand at end of week t
backlog_I = {t: LpVariable(f"bI_{t}", lowBound=0) for t in weeks}
backlog_II = {t: LpVariable(f"bII_{t}", lowBound=0) for t in weeks}

# Available skilled workers for production in week t
# = S0 - trainers busy in week t
# A trainer starting in week s is busy in weeks s and s+1
def trainers_busy(t):
    """Number of skilled workers busy training in week t"""
    expr = 0
    for s in n_train:
        if s <= t <= s + train_period - 1:
            expr += n_train[s]
    return expr

# Graduated trainees available in week t
def graduates_available(t):
    """Number of graduated trainees available in week t"""
    expr = 0
    for s in n_train:
        if s + train_period <= t:  # available from week s+2
            expr += train_cap * n_train[s]
    return expr

# Constraints for each week
for t in weeks:
    busy_t = trainers_busy(t)
    avail_skilled_t = S0 - busy_t  # skilled workers available for production
    grads_t = graduates_available(t)
    
    # Skilled workers available for production (non-overtime)
    # Some of these may do overtime
    # Normal skilled workers: avail_skilled_t (all get paid wage_skilled regardless)
    # Overtime workers: n_overtime[t] of the avail_skilled_t work overtime hours instead of normal
    
    # Actually, re-reading: skilled workers normally work 40h/week at 360 yuan
    # Overtime means they work 60h/week at 540 yuan (replaces normal schedule)
    # So a worker either works normal (40h, 360 yuan) or overtime (60h, 540 yuan)
    
    # Normal skilled hours available = (avail_skilled_t - n_overtime[t]) * normal_hours
    # Overtime skilled hours available = n_overtime[t] * overtime_hours
    
    prob += n_overtime[t] <= avail_skilled_t, f"ot_limit_{t}"
    
    # Hours constraints for skilled normal workers
    prob += h_I_s[t] + h_II_s[t] <= (avail_skilled_t - n_overtime[t]) * normal_hours, f"skilled_normal_hours_{t}"
    
    # Hours constraints for overtime workers
    prob += h_I_ot[t] + h_II_ot[t] <= n_overtime[t] * overtime_hours, f"skilled_ot_hours_{t}"
    
    # Hours constraints for graduates (they work normal_hours at wage_trainee_after)
    prob += h_I_g[t] + h_II_g[t] <= grads_t * normal_hours, f"grad_hours_{t}"
    
    # Production in week t
    prod_I_t = (h_I_s[t] + h_I_ot[t] + h_I_g[t]) * rate_I
    prod_II_t = (h_II_s[t] + h_II_ot[t] + h_II_g[t]) * rate_II
    
    # Backlog balance
    prev_bI = backlog_I[t-1] if t > 1 else 0
    prev_bII = backlog_II[t-1] if t > 1 else 0
    
    prob += backlog_I[t] >= prev_bI + demand[t]['I'] - prod_I_t, f"backlog_I_{t}"
    prob += backlog_II[t] >= prev_bII + demand[t]['II'] - prod_II_t, f"backlog_II_{t}"

# Training constraints: can't assign more trainers than available skilled workers
for t in weeks:
    if t <= T - 1:
        # Need enough skilled workers not already busy training
        pass  # This is implicitly handled by avail_skilled_t >= 0

# Ensure avail_skilled >= 0 for each week
for t in weeks:
    busy_t = trainers_busy(t)
    prob += S0 - busy_t >= 0, f"enough_skilled_{t}"

# Must train at least 50 new workers by end of week 8
total_trained = 0
for s in n_train:
    if s + train_period <= T:  # fully trained by end of week 8
        total_trained += train_cap * n_train[s]
    # What about those still in training? They won't count as trained.
    # Actually, "by the end of the 8th week" - training starting in week 7 finishes end of week 8
    # s + train_period - 1 <= T means s <= T - train_period + 1 = 7
    # So training starting in week 7: busy weeks 7,8, available week 9 - NOT by end of week 8
    # Training starting in week 6: busy weeks 6,7, available week 8 - YES
    # Wait, let me reconsider. If training starts week s, takes 2 weeks (s and s+1), 
    # then they graduate at end of week s+1, available from week s+2.
    # For them to be trained by end of week 8: s+1 <= 8, so s <= 7
    # But they're only "available" from week s+2. The goal says "trained by end of 8th week"
    # which means training completed by end of week 8: s + train_period - 1 <= 8, so s <= 7

# Let me recount: trained by end of week 8 means training is complete
total_trained_by_8 = 0
for s in n_train:
    if s + train_period - 1 <= T:  # training completes by end of week 8
        total_trained_by_8 += train_cap * n_train[s]

prob += total_trained_by_8 >= new_worker_goal, f"training_goal"

# Objective: minimize total cost
# Costs:
# 1. All skilled workers get paid every week (even trainers)
#    - Normal: wage_skilled per worker per week
#    - Overtime: wage_overtime per worker per week (instead of normal wage)
# 2. Trainees during training: wage_trainee_during per trainee per week
# 3. Graduated trainees: wage_trainee_after per graduate per week
# 4. Compensation fees for backlogs

total_cost = 0

for t in weeks:
    busy_t = trainers_busy(t)
    avail_skilled_t = S0 - busy_t
    grads_t = graduates_available(t)
    
    # Trainees currently in training in week t
    trainees_in_training = 0
    for s in n_train:
        if s <= t <= s + train_period - 1:
            trainees_in_training += train_cap * n_train[s]
    
    # Skilled worker wages: normal workers + overtime workers + trainers
    # Trainers get normal wage (they're skilled workers assigned to training)
    skilled_normal_cost = (avail_skilled_t - n_overtime[t]) * wage_skilled
    skilled_overtime_cost = n_overtime[t] * wage_overtime
    trainer_cost = busy_t * wage_skilled  # trainers still get skilled wage
    
    # Trainee wages
    trainee_training_cost = trainees_in_training * wage_trainee_during
    graduate_cost = grads_t * wage_trainee_after
    
    # Compensation
    comp_cost = comp_I * backlog_I[t] + comp_II * backlog_II[t]
    
    total_cost += skilled_normal_cost + skilled_overtime_cost + trainer_cost
    total_cost += trainee_training_cost + graduate_cost
    total_cost += comp_cost

prob += total_cost

# Solve
prob.solve(GUROBI_CMD(msg=0))

obj_val = value(prob.objective)

# Debug output
for t in weeks:
    busy = sum(value(n_train[s]) for s in n_train if s <= t <= s + train_period - 1)
    grads = sum(train_cap * value(n_train[s]) for s in n_train if s + train_period <= t)
    print(f"Week {t}: trainers_busy={busy}, grads={grads}, "
          f"hIs={value(h_I_s[t]):.1f}, hIIs={value(h_II_s[t]):.1f}, "
          f"hIot={value(h_I_ot[t]):.1f}, hIIot={value(h_II_ot[t]):.1f}, "
          f"hIg={value(h_I_g[t]):.1f}, hIIg={value(h_II_g[t]):.1f}, "
          f"bI={value(backlog_I[t]):.1f}, bII={value(backlog_II[t]):.1f}, "
          f"n_ot={value(n_overtime[t])}")

for s in sorted(n_train.keys()):
    print(f"Training start week {s}: {value(n_train[s])} trainers -> {train_cap * value(n_train[s])} trainees")

total_trained_val = sum(train_cap * value(n_train[s]) for s in n_train if s + train_period - 1 <= T)
print(f"Total trained by end of week 8: {total_trained_val}")

print(f"\nOBJECTIVE_VALUE: {obj_val}")