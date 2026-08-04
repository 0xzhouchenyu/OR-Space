import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import load_general_parameters, load_crop_data
import gurobi_pulp_compat as pulp

def main():
    # Load data
    params = load_general_parameters()
    crops, crop_data = load_crop_data()
    
    # Extract parameters
    land_area = params['land_area']
    funds_available = params['funds_available']
    labor_aw = params['labor_autumn_winter']
    labor_ss = params['labor_spring_summer']
    ext_rate_ss = params['external_work_rate_spring_summer']
    ext_rate_aw = params['external_work_rate_autumn_winter']
    
    inv_dairy = params['investment_per_dairy_cow']
    inv_chicken = params['investment_per_chicken']
    land_dairy = params['land_per_dairy_cow']
    labor_aw_dairy = params['labor_autumn_winter_per_dairy_cow']
    labor_ss_dairy = params['labor_spring_summer_per_dairy_cow']
    income_dairy = params['net_income_per_dairy_cow']
    labor_aw_chicken = params['labor_autumn_winter_per_chicken']
    labor_ss_chicken = params['labor_spring_summer_per_chicken']
    income_chicken = params['net_income_per_chicken']
    max_chickens = params['max_chickens']
    max_dairy_cows = params['max_dairy_cows']
    
    # Crop data
    # Person-days (Autumn/Winter), Person-days (Spring/Summer), Annual Net Income (Yuan/hectare)
    crop_aw = crop_data['Person-days (Autumn/Winter)']
    crop_ss = crop_data['Person-days (Spring/Summer)']
    crop_income = crop_data['Annual Net Income (Yuan/hectare)']
    
    # Create LP problem
    prob = pulp.LpProblem("Farm_Optimization", pulp.LpMaximize)
    
    # Decision variables
    # Crop areas
    x = {}
    for c in crops:
        x[c] = pulp.LpVariable(f"x_{c}", lowBound=0)
    
    # Number of dairy cows and chickens
    y_dairy = pulp.LpVariable("dairy_cows", lowBound=0, upBound=max_dairy_cows)
    y_chicken = pulp.LpVariable("chickens", lowBound=0, upBound=max_chickens)
    
    # Surplus labor for external work
    surplus_aw = pulp.LpVariable("surplus_aw", lowBound=0)
    surplus_ss = pulp.LpVariable("surplus_ss", lowBound=0)
    
    # Objective: maximize net income from crops + animals + external work
    obj = pulp.lpSum([crop_income[c] * x[c] for c in crops]) + \
          income_dairy * y_dairy + income_chicken * y_chicken + \
          ext_rate_aw * surplus_aw + ext_rate_ss * surplus_ss
    prob += obj
    
    # Land constraint
    prob += pulp.lpSum([x[c] for c in crops]) + land_dairy * y_dairy <= land_area, "Land"
    
    # Funds constraint
    prob += inv_dairy * y_dairy + inv_chicken * y_chicken <= funds_available, "Funds"
    
    # Labor autumn/winter constraint
    prob += pulp.lpSum([crop_aw[c] * x[c] for c in crops]) + \
            labor_aw_dairy * y_dairy + labor_aw_chicken * y_chicken + surplus_aw <= labor_aw, "Labor_AW"
    
    # Labor spring/summer constraint
    prob += pulp.lpSum([crop_ss[c] * x[c] for c in crops]) + \
            labor_ss_dairy * y_dairy + labor_ss_chicken * y_chicken + surplus_ss <= labor_ss, "Labor_SS"
    
    # Solve
    prob.solve(pulp.GUROBI_CMD(msg=0))
    
    # Output results
    if prob.status == pulp.constants.LpStatusOptimal:
        obj_val = pulp.value(prob.objective)
        
        # Print solution details
        for c in crops:
            print(f"{c}: {pulp.value(x[c]):.4f} hectares")
        print(f"Dairy cows: {pulp.value(y_dairy):.4f}")
        print(f"Chickens: {pulp.value(y_chicken):.4f}")
        print(f"Surplus labor AW: {pulp.value(surplus_aw):.4f} person-days")
        print(f"Surplus labor SS: {pulp.value(surplus_ss):.4f} person-days")
        print(f"OBJECTIVE_VALUE: {obj_val}")
    else:
        print(f"Problem status: {pulp.LpStatus[prob.status]}")
        print("OBJECTIVE_VALUE: 0")

if __name__ == "__main__":
    main()