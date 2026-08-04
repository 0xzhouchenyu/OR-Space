import os
import csv
from gurobi_pulp_compat import *

def main():
    # Parse table_1.csv
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    
    # Processing times (hours per unit) from table_1.csv
    # Equipment, Product_I, Product_II, Product_III, Effective_Machine_Hours, Processing_Cost_per_Machine_Hour
    proc_time = {}  # (equipment, product) -> hours per unit
    capacity = {}   # equipment -> available hours
    cost_rate = {}  # equipment -> cost per machine hour
    
    with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            equip = row['Equipment'].strip()
            if equip == 'Raw_Material_Cost':
                raw_cost = {'I': float(row['Product_I']), 'II': float(row['Product_II']), 'III': float(row['Product_III'])}
            elif equip == 'Unit_Price':
                price = {'I': float(row['Product_I']), 'II': float(row['Product_II']), 'III': float(row['Product_III'])}
            else:
                for prod, col in [('I', 'Product_I'), ('II', 'Product_II'), ('III', 'Product_III')]:
                    val = row[col].strip()
                    if val != '-':
                        proc_time[(equip, prod)] = float(val)
                capacity[equip] = float(row['Effective_Machine_Hours'])
                cost_rate[equip] = float(row['Processing_Cost_per_Machine_Hour'])
    
    # Equipment assignments from general_parameters (confirmed by proc_time keys)
    stage_A_equip = {'I': ['A1', 'A2'], 'II': ['A1', 'A2'], 'III': ['A2']}
    stage_B_equip = {'I': ['B1', 'B2', 'B3'], 'II': ['B1'], 'III': ['B2']}
    
    prob = LpProblem("Factory_Production", LpMaximize)
    
    # Decision variables: x[(equip, prod)] = units of product processed on equipment
    x = {}
    for prod in ['I', 'II', 'III']:
        for equip in stage_A_equip[prod]:
            x[(equip, prod)] = LpVariable(f"x_{equip}_{prod}", lowBound=0)
        for equip in stage_B_equip[prod]:
            x[(equip, prod)] = LpVariable(f"x_{equip}_{prod}", lowBound=0)
    
    # Total production of each product (defined by stage A flow = stage B flow)
    total = {}
    for prod in ['I', 'II', 'III']:
        total[prod] = lpSum(x[(e, prod)] for e in stage_A_equip[prod])
        # Flow conservation: stage A total == stage B total
        prob += lpSum(x[(e, prod)] for e in stage_A_equip[prod]) == lpSum(x[(e, prod)] for e in stage_B_equip[prod])
    
    # Capacity constraints
    for equip in ['A1', 'A2', 'B1', 'B2', 'B3']:
        relevant = [(equip, prod) for prod in ['I', 'II', 'III'] if (equip, prod) in x]
        if relevant:
            prob += lpSum(proc_time[(equip, prod)] * x[(equip, prod)] for equip2, prod in relevant) <= capacity[equip]
    
    # Objective: profit = revenue - raw material - processing cost
    revenue = lpSum(price[p] * total[p] for p in ['I', 'II', 'III'])
    raw_mat = lpSum(raw_cost[p] * total[p] for p in ['I', 'II', 'III'])
    proc_cost = lpSum(cost_rate[e] * proc_time[(e, p)] * x[(e, p)] for (e, p) in x)
    
    prob += revenue - raw_mat - proc_cost
    
    prob.solve(GUROBI_CMD(msg=0))
    
    print(f"Status: {LpStatus[prob.status]}")
    for v in prob.variables():
        if v.varValue and v.varValue > 0:
            print(f"{v.name} = {v.varValue}")
    
    print(f"OBJECTIVE_VALUE: {value(prob.objective):.2f}")

main()