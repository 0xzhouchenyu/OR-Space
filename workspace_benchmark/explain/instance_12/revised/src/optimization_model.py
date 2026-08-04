import os
import csv
from gurobi_pulp_compat import LpProblem, LpMinimize, LpVariable, lpSum, GUROBI_CMD, value

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, '..', 'data')

    # Load container data
    containers = []
    with open(os.path.join(data_dir, 'table_1.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            containers.append({
                'code': int(row['Container_Type_Code']),
                'volume': int(row['Volume_cm3']),
                'demand': int(row['Market_Demand_units']),
                'cost': float(row['Unit_Variable_Production_Cost_Yuan_per_unit'])
            })

    # Load general parameters
    fixed_cost = None
    energy_cost_per_kwh = None
    max_total_energy_kwh = None
    eco_capacity_share = None
    eco_overhead_cost = None
    regular_energy_intensity = None
    eco_energy_intensity = None

    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['Parameter_Name'].strip()
            value_f = float(row['Value'])
            if name == 'fixed_setup_cost':
                fixed_cost = value_f
            elif name == 'energy_cost_per_kwh':
                energy_cost_per_kwh = value_f
            elif name == 'max_total_energy_kwh':
                max_total_energy_kwh = value_f
            elif name == 'eco_capacity_share':
                eco_capacity_share = value_f
            elif name == 'eco_overhead_cost':
                eco_overhead_cost = value_f
            elif name == 'regular_energy_intensity_kwh_per_unit':
                regular_energy_intensity = value_f
            elif name == 'eco_energy_intensity_kwh_per_unit':
                eco_energy_intensity = value_f

    n = len(containers)

    # Create the problem
    prob = LpProblem("PlasticContainers_EnergyModes", LpMinimize)

    # Binary setup variables for each mode
    y_regular = {i: LpVariable(f"y_regular_{i}", cat='Binary') for i in range(n)}
    y_eco = {i: LpVariable(f"y_eco_{i}", cat='Binary') for i in range(n)}

    # Production variables per mode and demand
    x_regular = {}
    x_eco = {}
    for i in range(n):
        for j in range(n):
            if containers[i]['volume'] >= containers[j]['volume']:
                x_regular[i, j] = LpVariable(f"x_regular_{i}_{j}", lowBound=0, cat='Integer')
                x_eco[i, j] = LpVariable(f"x_eco_{i}_{j}", lowBound=0, cat='Integer')

    # Variable production cost (same cost for both modes)
    var_cost_expr = lpSum(containers[i]['cost'] * (x_regular[i, j] + x_eco[i, j]) for (i, j) in x_regular)

    # Setup and overhead costs
    setup_cost_expr = lpSum(fixed_cost * y_regular[i] for i in range(n)) + lpSum(fixed_cost * y_eco[i] for i in range(n))
    eco_overhead_expr = lpSum(eco_overhead_cost * y_eco[i] for i in range(n))

    # Total production per type and mode
    total_regular = {i: lpSum(x_regular[i, j] for j in range(n) if (i, j) in x_regular) for i in range(n)}
    total_eco = {i: lpSum(x_eco[i, j] for j in range(n) if (i, j) in x_eco) for i in range(n)}

    # Energy use and cost
    total_energy = lpSum(regular_energy_intensity * total_regular[i] + eco_energy_intensity * total_eco[i] for i in range(n))
    energy_cost_expr = energy_cost_per_kwh * total_energy

    # Objective
    prob += var_cost_expr + setup_cost_expr + eco_overhead_expr + energy_cost_expr

    # Demand constraints
    for j in range(n):
        prob += (
            lpSum(x_regular[i, j] + x_eco[i, j] for i in range(n) if (i, j) in x_regular) >= containers[j]['demand'],
            f"demand_{j}"
        )

    # Big-M for setup linking
    M = sum(c['demand'] for c in containers)
    for i in range(n):
        prob += (total_regular[i] <= M * y_regular[i], f"setup_regular_{i}")
        prob += (total_eco[i] <= M * y_eco[i], f"setup_eco_{i}")

    # Eco capacity share constraints
    for i in range(n):
        lhs = (1.0 - eco_capacity_share) * total_eco[i]
        rhs = eco_capacity_share * total_regular[i]
        prob += (lhs <= rhs, f"eco_share_{i}")

    # Total energy cap
    prob += (total_energy <= max_total_energy_kwh, "energy_cap")

    # Solve
    prob.solve(GUROBI_CMD(msg=0))

    obj_val = value(prob.objective)

    # Optional solution details
    for i in range(n):
        reg_prod = value(total_regular[i])
        eco_prod = value(total_eco[i])
        if reg_prod is not None and eco_prod is not None and (reg_prod > 0 or eco_prod > 0):
            print(f"Container type {containers[i]['code']}: regular={reg_prod}, eco={eco_prod}, y_reg={int(value(y_regular[i]))}, y_eco={int(value(y_eco[i]))}")

    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()
