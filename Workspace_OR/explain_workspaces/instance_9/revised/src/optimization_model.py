import os
import pandas as pd
from gurobi_pulp_compat import LpProblem, LpMaximize, LpVariable, lpSum, GUROBI_CMD, LpStatus, value

data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
toys_df = pd.read_csv(os.path.join(data_dir, 'table_1.csv'))
params_df = pd.read_csv(os.path.join(data_dir, 'general_parameters.csv'))
params = {row['Parameter_Name'].strip(): float(row['Value']) for _, row in params_df.iterrows()}

toys = []
for _, r in toys_df.iterrows():
    toys.append({
        'type': r['Toy_Type'].strip(),
        'profit': float(r['Profit_Per_Unit']),
        'wood': float(r['Wood_Required_Per_Unit']),
        'steel': float(r['Steel_Required_Per_Unit']),
    })

available_wood = params['available_wood']
available_steel = params['available_steel']
bonus = params['profit_premium_bonus']
steel_factor = params['premium_steel_factor']
premium_cap = params['premium_shift_capacity']
M = 1000

prob = LpProblem('HausToys_DualShift', LpMaximize)

xS = {t['type']: LpVariable(f"xS_{t['type']}", lowBound=0) for t in toys}
xP = {t['type']: LpVariable(f"xP_{t['type']}", lowBound=0) for t in toys}
yS = {t['type']: LpVariable(f"yS_{t['type']}", cat='Binary') for t in toys}
yP = {t['type']: LpVariable(f"yP_{t['type']}", cat='Binary') for t in toys}

prob += lpSum([t['profit'] * xS[t['type']] for t in toys]) + \
        lpSum([(t['profit'] + bonus) * xP[t['type']] for t in toys])

prob += lpSum([t['wood'] * (xS[t['type']] + xP[t['type']]) for t in toys]) <= available_wood
prob += lpSum([t['steel'] * xS[t['type']] for t in toys]) + \
        lpSum([t['steel'] * steel_factor * xP[t['type']] for t in toys]) <= available_steel
prob += lpSum([xP[t['type']] for t in toys]) <= premium_cap

for t in toys:
    prob += yS[t['type']] + yP[t['type']] <= 1
    prob += xS[t['type']] <= M * yS[t['type']]
    prob += xP[t['type']] <= M * yP[t['type']]

prob += (yS['truck'] + yP['truck']) + (yS['train'] + yP['train']) <= 1
prob += (yS['boat'] + yP['boat']) <= (yS['airplane'] + yP['airplane'])
prob += xS['boat'] + xP['boat'] <= xS['train'] + xP['train']

prob.solve(GUROBI_CMD(msg=0))

print(f"Status: {LpStatus[prob.status]}")
for t in toys:
    print(f"{t['type']}: S={value(xS[t['type']]):.2f} P={value(xP[t['type']]):.2f} (yS={value(yS[t['type']])}, yP={value(yP[t['type']])})")

obj_val = value(prob.objective)
print(f"OBJECTIVE_VALUE: {obj_val}")
