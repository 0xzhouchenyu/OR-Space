import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import load_demand, load_parameters
import gurobi_pulp_compat as pulp

def main():
    demand_data = load_demand()
    params = load_parameters()
    
    # Planning months: July to December
    months = ['July', 'August', 'September', 'October', 'November', 'December']
    products = ['Product_I', 'Product_II']
    
    # Parameters
    cost_I = params['product_I_cost_jun_to_dec']  # 4.5 for June-Dec
    cost_II = params['product_II_cost_jun_to_dec']  # 7 for June-Dec
    prod_cost = {'Product_I': cost_I, 'Product_II': cost_II}
    
    max_cap = int(params['max_production_capacity'])  # 120,000
    vol_I = params['product_I_volume']  # 0.2
    vol_II = params['product_II_volume']  # 0.4
    volume = {'Product_I': vol_I, 'Product_II': vol_II}
    
    warehouse_cap = params['warehouse_capacity']  # 15,000 cubic meters
    own_cost = params['own_warehouse_cost']  # 1 yuan/m³/month
    ext_cost = params['external_warehouse_cost']  # 1.5 yuan/m³/month
    
    # Demand for planning months
    demand = {}
    for m in months:
        for p in products:
            demand[(m, p)] = demand_data[(m, p)]
    
    # Model
    prob = pulp.LpProblem("Production_Planning", pulp.LpMinimize)
    
    # Decision variables
    # Production quantities
    x = pulp.LpVariable.dicts("prod", [(m, p) for m in months for p in products], lowBound=0, cat='Continuous')
    
    # Inventory at end of month
    inv = pulp.LpVariable.dicts("inv", [(m, p) for m in months for p in products], lowBound=0, cat='Continuous')
    
    # Own warehouse usage (cubic meters)
    own_wh = pulp.LpVariable.dicts("own_wh", months, lowBound=0, cat='Continuous')
    
    # External warehouse usage (cubic meters)
    ext_wh = pulp.LpVariable.dicts("ext_wh", months, lowBound=0, cat='Continuous')
    
    # Objective: minimize production cost + inventory holding cost
    prob += (
        pulp.lpSum(prod_cost[p] * x[(m, p)] for m in months for p in products) +
        pulp.lpSum(own_cost * own_wh[m] + ext_cost * ext_wh[m] for m in months)
    )
    
    # Constraints
    for i, m in enumerate(months):
        # Inventory balance
        for p in products:
            if i == 0:
                prob += inv[(m, p)] == 0 + x[(m, p)] - demand[(m, p)]
            else:
                prev_m = months[i - 1]
                prob += inv[(m, p)] == inv[(prev_m, p)] + x[(m, p)] - demand[(m, p)]
        
        # Production capacity
        prob += pulp.lpSum(x[(m, p)] for p in products) <= max_cap
        
        # Warehouse: total volume of inventory
        total_vol = pulp.lpSum(volume[p] * inv[(m, p)] for p in products)
        prob += own_wh[m] + ext_wh[m] >= total_vol
        prob += own_wh[m] <= warehouse_cap
    
    # Solve
    prob.solve(pulp.GUROBI_CMD(msg=0))
    
    obj_val = pulp.value(prob.objective)
    
    # Debug output
    for m in months:
        for p in products:
            print(f"{m} {p}: produce={pulp.value(x[(m,p)]):.0f}, inv={pulp.value(inv[(m,p)]):.0f}, demand={demand[(m,p)]}")
        print(f"  Own WH: {pulp.value(own_wh[m]):.0f}, Ext WH: {pulp.value(ext_wh[m]):.0f}")
    
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()