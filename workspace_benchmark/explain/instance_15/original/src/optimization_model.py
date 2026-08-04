import gurobi_pulp_compat as pulp
from utils import load_data

def solve():
    param_dict, demand = load_data()
    
    n = int(param_dict['n'])
    cost_new = float(param_dict['cost_new_tool'])
    cost_slow = float(param_dict['cost_slow_repair'])
    cost_fast = float(param_dict['cost_fast_repair'])
    dur_slow = int(param_dict['slow_repair_duration'])
    dur_fast = int(param_dict['fast_repair_duration'])
    
    prob = pulp.LpProblem("Tool_Repair_Problem", pulp.LpMinimize)
    
    stages = list(range(1, n + 1))
    x = pulp.LpVariable.dicts("buy", stages, lowBound=0, cat='Integer')
    y = pulp.LpVariable.dicts("fast", stages, lowBound=0, cat='Integer')
    z = pulp.LpVariable.dicts("slow", stages, lowBound=0, cat='Integer')
    c = pulp.LpVariable.dicts("clean", [0] + stages, lowBound=0, cat='Integer')
    d = pulp.LpVariable.dicts("dirty", [0] + stages, lowBound=0, cat='Integer')
    
    prob += c[0] == 0
    prob += d[0] == 0
    
    for i in stages:
        fast_ready = y[i - dur_fast - 1] if i - dur_fast - 1 >= 1 else 0
        slow_ready = z[i - dur_slow - 1] if i - dur_slow - 1 >= 1 else 0
        
        prob += x[i] + c[i-1] + fast_ready + slow_ready == demand[i] + c[i]
        prob += demand[i] + d[i-1] == y[i] + z[i] + d[i]
        
    prob += pulp.lpSum([cost_new * x[i] + cost_fast * y[i] + cost_slow * z[i] for i in stages])
    
    prob.solve(pulp.GUROBI_CMD(msg=False))
    
    print(f"OBJECTIVE_VALUE: {pulp.value(prob.objective)}")

if __name__ == "__main__":
    solve()