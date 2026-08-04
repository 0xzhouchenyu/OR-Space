import os
import sys
from utils import load_data
import gurobi_pulp_compat as pulp

def main():
    # Load and parse data
    data = load_data()
    
    # Decision variables: x[i][j] = kg of raw material i used in brand j
    # Raw materials: 0=A, 1=B, 2=C
    # Brands: 0=A, 1=B, 2=C
    
    prob = pulp.LpProblem("CandyFactory", pulp.LpMaximize)
    
    # x[i][j]: amount of raw material i in brand j
    raw_materials = ['A', 'B', 'C']
    brands = ['A', 'B', 'C']
    
    x = {}
    for i in range(3):
        for j in range(3):
            x[i, j] = pulp.LpVariable(f"x_{i}_{j}", lowBound=0)
    
    # Total production of each brand
    y = {}
    for j in range(3):
        y[j] = pulp.lpSum(x[i, j] for i in range(3))
    
    # Raw material costs
    raw_cost = [2.00, 1.50, 1.00]
    # Processing fees per brand
    proc_fee = [0.50, 0.40, 0.30]
    # Selling prices per brand
    sell_price = [3.40, 2.85, 2.25]
    # Monthly limits for raw materials
    limits = [2000, 2500, 1200]
    
    # Objective: maximize profit
    revenue = pulp.lpSum(sell_price[j] * y[j] for j in range(3))
    material_cost = pulp.lpSum(raw_cost[i] * x[i, j] for i in range(3) for j in range(3))
    processing_cost = pulp.lpSum(proc_fee[j] * y[j] for j in range(3))
    
    prob += revenue - material_cost - processing_cost
    
    # Raw material supply constraints
    for i in range(3):
        prob += pulp.lpSum(x[i, j] for j in range(3)) <= limits[i]
    
    # Composition constraints (percentage constraints)
    # Raw material A (i=0): >=60% in brand A (j=0), >=15% in brand B (j=1)
    prob += x[0, 0] >= 0.60 * y[0]  # RM A >= 60% of Brand A
    prob += x[0, 1] >= 0.15 * y[1]  # RM A >= 15% of Brand B
    
    # Raw material C (i=2): <=20% in brand A (j=0), <=60% in brand B (j=1), <=50% in brand C (j=2)
    prob += x[2, 0] <= 0.20 * y[0]  # RM C <= 20% of Brand A
    prob += x[2, 1] <= 0.60 * y[1]  # RM C <= 60% of Brand B
    prob += x[2, 2] <= 0.50 * y[2]  # RM C <= 50% of Brand C
    
    # Solve
    prob.solve(pulp.GUROBI_CMD(msg=0))
    
    print(f"Status: {pulp.LpStatus[prob.status]}")
    for j in range(3):
        print(f"Brand {brands[j]} production: {pulp.value(y[j]):.2f} kg")
    for i in range(3):
        for j in range(3):
            if pulp.value(x[i, j]) > 0.01:
                print(f"  RM {raw_materials[i]} in Brand {brands[j]}: {pulp.value(x[i, j]):.2f}")
    
    obj = pulp.value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj:.1f}")

if __name__ == "__main__":
    main()