import os
import pandas as pd
import gurobi_pulp_compat as pulp

def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

    t1 = pd.read_csv(os.path.join(data_dir, 'table_1.csv'))
    gp = pd.read_csv(os.path.join(data_dir, 'general_parameters.csv'))
    params = {row['Parameter_Name'].strip(): float(row['Value']) for _, row in gp.iterrows()}

    products = ['Product_I', 'Product_II', 'Product_III']
    equipment = [str(e).strip() for e in t1['Equipment'].tolist()]
    proc_times = {}
    eff_hours = {}
    op_costs = {}
    for _, row in t1.iterrows():
        e = str(row['Equipment']).strip()
        proc_times[e] = {}
        for p in products:
            v = row[p]
            proc_times[e][p] = float(v) if pd.notna(v) and str(v).strip() != '' else None
        eff_hours[e] = float(row['Effective_Machine_Hours'])
        op_costs[e] = float(row['Operating_Costs_Full_Capacity_Yuan'])

    raw_costs = {
        'Product_I': params['raw_material_cost_product_I'],
        'Product_II': params['raw_material_cost_product_II'],
        'Product_III': params['raw_material_cost_product_III'],
    }
    prices = {
        'Product_I': params['unit_price_product_I'],
        'Product_II': params['unit_price_product_II'],
        'Product_III': params['unit_price_product_III'],
    }
    labor_coeff = {
        'A1': params['labor_coeff_A1'],
        'A2': params['labor_coeff_A2'],
        'B1': params['labor_coeff_B1'],
        'B2': params['labor_coeff_B2'],
        'B3': params['labor_coeff_B3'],
    }
    shared_labor_hours = params['shared_labor_hours']
    b2_fee = params['b2_activation_fee']

    A_equip = [e for e in equipment if e.startswith('A')]
    B_equip = [e for e in equipment if e.startswith('B')]

    model = pulp.LpProblem("Factory_Production_Revised", pulp.LpMaximize)

    x = {}
    for e in equipment:
        x[e] = {}
        for p in products:
            if proc_times[e][p] is not None:
                x[e][p] = pulp.LpVariable(f"x_{e}_{p}", lowBound=0)

    z_B2 = pulp.LpVariable("z_B2", cat='Binary')

    # Capacity constraints
    for e in equipment:
        model += (
            pulp.lpSum(x[e][p] * proc_times[e][p] for p in products if proc_times[e][p] is not None) <= eff_hours[e],
            f"capacity_{e}"
        )

    # B2 activation linkage (big-M)
    model += (
        pulp.lpSum(x['B2'][p] * proc_times['B2'][p] for p in products if proc_times['B2'][p] is not None)
        <= eff_hours['B2'] * z_B2,
        "b2_activation_link"
    )

    # Flow balance
    for p in products:
        a_sum = pulp.lpSum(x[e][p] for e in A_equip if proc_times[e][p] is not None)
        b_sum = pulp.lpSum(x[e][p] for e in B_equip if proc_times[e][p] is not None)
        model += (a_sum == b_sum, f"balance_{p}")

    # Shared labor pool constraint
    labor_used = pulp.lpSum(
        labor_coeff[e] * pulp.lpSum(x[e][p] * proc_times[e][p] for p in products if proc_times[e][p] is not None)
        for e in equipment
    )
    model += (labor_used <= shared_labor_hours, "shared_labor_pool")

    total_prod = {p: pulp.lpSum(x[e][p] for e in A_equip if proc_times[e][p] is not None) for p in products}

    revenue = pulp.lpSum(prices[p] * total_prod[p] for p in products)
    raw_cost_total = pulp.lpSum(raw_costs[p] * total_prod[p] for p in products)
    operating_cost = pulp.lpSum(
        op_costs[e] * pulp.lpSum(x[e][p] * proc_times[e][p] for p in products if proc_times[e][p] is not None) / eff_hours[e]
        for e in equipment
    )
    activation_cost = b2_fee * z_B2

    model += revenue - raw_cost_total - operating_cost - activation_cost

    model.solve(pulp.GUROBI_CMD(msg=0))
    obj_val = pulp.value(model.objective)
    print(f"OBJECTIVE_VALUE: {obj_val:.4f}")

if __name__ == "__main__":
    main()
