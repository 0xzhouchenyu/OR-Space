import csv
import math
import gurobi_pulp_compat as pulp
from utils import get_data_path

def solve():
    table_1_path = get_data_path('table_1.csv')
    orders = []
    with open(table_1_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            orders.append({
                'width': float(row['Width_meters']),
                'length': float(row['Length_meters'])
            })
            
    params_path = get_data_path('general_parameters.csv')
    std_widths = []
    with open(params_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if 'standard_width' in row['Parameter_Name']:
                std_widths.append(float(row['Value']))
                
    widths = [o['width'] for o in orders]
    lengths = [o['length'] for o in orders]
    
    total_required_area = sum(w * l for w, l in zip(widths, lengths))
    
    patterns_by_std_width = {}
    for idx, sw in enumerate(std_widths):
        patterns = []
        def build_pattern(index, current_pattern, current_sum):
            if index == len(widths):
                if any(c > 0 for c in current_pattern):
                    patterns.append(current_pattern)
                return
            
            max_count = int(math.floor((sw - current_sum + 1e-7) / widths[index]))
            for count in range(max_count + 1):
                build_pattern(index + 1, current_pattern + [count], current_sum + count * widths[index])
                
        build_pattern(0, [], 0.0)
        patterns_by_std_width[idx] = {'sw': sw, 'patterns': patterns}
        
    prob = pulp.LpProblem("Minimize_Waste", pulp.LpMinimize)
    
    x_vars = {}
    for idx, data in patterns_by_std_width.items():
        for i, p in enumerate(data['patterns']):
            x_vars[(idx, i)] = pulp.LpVariable(f"x_{idx}_{i}", lowBound=0, cat='Continuous')
            
    # Objective: Minimize total area used
    prob += pulp.lpSum(data['sw'] * x_vars[(idx, i)] for idx, data in patterns_by_std_width.items() for i, p in enumerate(data['patterns']))
    
    # Constraints: Satisfy length requirements for each order width
    for j in range(len(widths)):
        prob += pulp.lpSum(p[j] * x_vars[(idx, i)] for idx, data in patterns_by_std_width.items() for i, p in enumerate(data['patterns'])) >= lengths[j]
        
    prob.solve(pulp.GUROBI_CMD(msg=False))
    
    total_area_used = pulp.value(prob.objective)
    waste = total_area_used - total_required_area
    
    print(f"OBJECTIVE_VALUE: {round(waste, 4)}")

if __name__ == "__main__":
    solve()