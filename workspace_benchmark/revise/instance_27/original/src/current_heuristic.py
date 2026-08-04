import os
import csv
from utils import load_table1, load_general_params
import gurobi_pulp_compat as pulp

def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    
    equipment, proc_times, eff_hours, op_costs = load_table1(data_dir)
    raw_costs, prices = load_general_params(data_dir)
    
    products = ['Product_I', 'Product_II', 'Product_III']
    prod_idx = {p: i for i, p in enumerate(products)}
    
    A_equip = [e for e in equipment if e.startswith('A')]
    B_equip = [e for e in equipment if e.startswith('B')]
    
    model = pulp.LpProblem("Factory_Production", pulp.LpMaximize)
    
    # x[e][p] = number of units of product p processed on equipment e
    x = {}
    for e in equipment:
        x[e] = {}
        for p in products:
            if proc_times[e][p] is not None:
                x[e][p] = pulp.LpVariable(f"x_{e}_{p}", lowBound=0)
    
    # Fraction of capacity used by each equipment
    # f[e] = sum of (x[e][p] * proc_times[e][p]) / eff_hours[e]
    
    # Capacity constraints: total processing time <= effective machine hours
    for e in equipment:
        model += (
            pulp.lpSum(x[e][p] * proc_times[e][p] for p in products if proc_times[e][p] is not None) <= eff_hours[e],
            f"capacity_{e}"
        )
    
    # Flow balance: for each product, total A-processed = total B-processed
    for p in products:
        a_sum = pulp.lpSum(x[e][p] for e in A_equip if proc_times[e][p] is not None)
        b_sum = pulp.lpSum(x[e][p] for e in B_equip if proc_times[e][p] is not None)
        model += (a_sum == b_sum, f"balance_{p}")
    
    # Total production of each product
    total_prod = {}
    for p in products:
        total_prod[p] = pulp.lpSum(x[e][p] for e in A_equip if proc_times[e][p] is not None)
    
    # Revenue
    revenue = pulp.lpSum(prices[p] * total_prod[p] for p in products)
    
    # Raw material costs
    raw_cost_total = pulp.lpSum(raw_costs[p] * total_prod[p] for p in products)
    
    # Operating costs: proportional to usage fraction
    operating_cost = pulp.lpSum(
        op_costs[e] * pulp.lpSum(x[e][p] * proc_times[e][p] for p in products if proc_times[e][p] is not None) / eff_hours[e]
        for e in equipment
    )
    
    # Objective: maximize profit
    model += revenue - raw_cost_total - operating_cost
    
    model.solve(pulp.GUROBI_CMD(msg=0))
    
    obj_val = pulp.value(model.objective)
    
    for e in equipment:
        for p in products:
            if proc_times[e][p] is not None:
                val = x[e][p].varValue
                if val and val > 1e-6:
                    print(f"  {e} -> {p}: {val:.4f} units")
    
    print(f"OBJECTIVE_VALUE: {obj_val:.4f}")

if __name__ == "__main__":
    main()