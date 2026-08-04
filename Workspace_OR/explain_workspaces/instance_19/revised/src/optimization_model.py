import os
from utils import load_general_parameters
import gurobi_pulp_compat as pulp

data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
params = load_general_parameters(os.path.join(data_dir, 'general_parameters.csv'))

cost_A = params['cost_per_chair_A']
cost_B = params['cost_per_chair_B']
cost_C = params['cost_per_chair_C']
chairs_per_order_A = params['chairs_per_order_A']
chairs_per_order_B = params['chairs_per_order_B']
chairs_per_order_C = params['chairs_per_order_C']
min_total = params['min_total_chairs']
max_total = params['max_total_chairs']
min_chairs_B_if_A = params['min_chairs_B_if_A']
dependency_B_C = params['dependency_B_C']
fixed_fee_A_regular = params['fixed_fee_A_regular']
fixed_fee_A_express = params['fixed_fee_A_express']
fixed_fee_B_regular = params['fixed_fee_B_regular']
fixed_fee_B_express = params['fixed_fee_B_express']
fixed_fee_C_regular = params['fixed_fee_C_regular']
fixed_fee_C_express = params['fixed_fee_C_express']
weekly_order_budget = params['weekly_order_budget']

prob = pulp.LpProblem("FurnitureOrder", pulp.LpMinimize)

max_orders_A = int(max_total // int(chairs_per_order_A)) + 1
max_orders_B = int(max_total // int(chairs_per_order_B)) + 1
max_orders_C = int(max_total // int(chairs_per_order_C)) + 1

orders_A_regular = pulp.LpVariable("orders_A_regular", lowBound=0, upBound=max_orders_A, cat='Integer')
orders_A_express = pulp.LpVariable("orders_A_express", lowBound=0, upBound=max_orders_A, cat='Integer')
orders_B_regular = pulp.LpVariable("orders_B_regular", lowBound=0, upBound=max_orders_B, cat='Integer')
orders_B_express = pulp.LpVariable("orders_B_express", lowBound=0, upBound=max_orders_B, cat='Integer')
orders_C_regular = pulp.LpVariable("orders_C_regular", lowBound=0, upBound=max_orders_C, cat='Integer')
orders_C_express = pulp.LpVariable("orders_C_express", lowBound=0, upBound=max_orders_C, cat='Integer')

y_A_regular = pulp.LpVariable("y_A_regular", cat='Binary')
y_A_express = pulp.LpVariable("y_A_express", cat='Binary')
y_B_regular = pulp.LpVariable("y_B_regular", cat='Binary')
y_B_express = pulp.LpVariable("y_B_express", cat='Binary')
y_C_regular = pulp.LpVariable("y_C_regular", cat='Binary')
y_C_express = pulp.LpVariable("y_C_express", cat='Binary')

M_A = max_orders_A
M_B = max_orders_B
M_C = max_orders_C

prob += orders_A_regular <= M_A * y_A_regular
prob += orders_A_regular >= y_A_regular
prob += orders_A_express <= M_A * y_A_express
prob += orders_A_express >= y_A_express
prob += orders_B_regular <= M_B * y_B_regular
prob += orders_B_regular >= y_B_regular
prob += orders_B_express <= M_B * y_B_express
prob += orders_B_express >= y_B_express
prob += orders_C_regular <= M_C * y_C_regular
prob += orders_C_regular >= y_C_regular
prob += orders_C_express <= M_C * y_C_express
prob += orders_C_express >= y_C_express

prob += y_A_regular + y_A_express <= 1
prob += y_B_regular + y_B_express <= 1
prob += y_C_regular + y_C_express <= 1

prob += (y_A_regular + y_A_express + y_B_regular + y_B_express + y_C_regular + y_C_express) <= weekly_order_budget

chairs_A = chairs_per_order_A * (orders_A_regular + orders_A_express)
chairs_B = chairs_per_order_B * (orders_B_regular + orders_B_express)
chairs_C = chairs_per_order_C * (orders_C_regular + orders_C_express)

prob += chairs_A + chairs_B + chairs_C >= min_total
prob += chairs_A + chairs_B + chairs_C <= max_total

prob += chairs_B >= min_chairs_B_if_A * (y_A_regular + y_A_express)

if dependency_B_C != 0:
    prob += (y_B_regular + y_B_express) <= (y_C_regular + y_C_express)

prob += (cost_A * chairs_A + cost_B * chairs_B + cost_C * chairs_C +
         fixed_fee_A_regular * y_A_regular + fixed_fee_A_express * y_A_express +
         fixed_fee_B_regular * y_B_regular + fixed_fee_B_express * y_B_express +
         fixed_fee_C_regular * y_C_regular + fixed_fee_C_express * y_C_express)

prob.solve(pulp.GUROBI_CMD(msg=0))

obj_val = pulp.value(prob.objective)
print(f"OBJECTIVE_VALUE: {obj_val}")
