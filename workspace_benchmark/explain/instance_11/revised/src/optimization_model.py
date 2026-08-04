import os
import pandas as pd
import gurobi_pulp_compat as pulp


def solve():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    table_1_path = os.path.join(data_dir, 'table_1.csv')
    params_path = os.path.join(data_dir, 'general_parameters.csv')

    df1 = pd.read_csv(table_1_path)
    df_params = pd.read_csv(params_path)

    row_a = df1[df1['Type'] == 'Type_A'].iloc[0]
    row_b = df1[df1['Type'] == 'Type_B'].iloc[0]
    row_cap = df1[df1['Type'] == 'Max_weekly_capacity'].iloc[0]
    row_cost = df1[df1['Type'] == 'Process_cost_Yuan_per_hour'].iloc[0]

    mfg_a = float(row_a['Manufacturing_hours_per_unit'])
    asm_a = float(row_a['Assembly_hours_per_unit'])
    insp_a_orig = float(row_a['Inspection_hours_per_unit'])
    price_a = float(row_a['Selling_Price_Yuan_per_unit'])

    mfg_b = float(row_b['Manufacturing_hours_per_unit'])
    asm_b = float(row_b['Assembly_hours_per_unit'])
    insp_b_orig = float(row_b['Inspection_hours_per_unit'])
    price_b = float(row_b['Selling_Price_Yuan_per_unit'])

    cap_mfg = float(row_cap['Manufacturing_hours_per_unit'])
    cap_asm = float(row_cap['Assembly_hours_per_unit'])
    cap_insp = float(row_cap['Inspection_hours_per_unit'])

    cost_mfg = float(row_cost['Manufacturing_hours_per_unit'])
    cost_asm = float(row_cost['Assembly_hours_per_unit'])
    cost_insp_orig = float(row_cost['Inspection_hours_per_unit'])

    def get_param(name):
        return float(df_params[df_params['Parameter_Name'] == name]['Value'].iloc[0])

    min_profit = get_param('min_weekly_profit')
    min_a = get_param('min_type_a_production')

    insp_a_M = get_param('insp_a_M')
    insp_b_M = get_param('insp_b_M')
    insp_a_E = get_param('insp_a_E')
    insp_b_E = get_param('insp_b_E')

    cap_ext = get_param('cap_ext')

    cost_insp_M = get_param('cost_insp_M')
    cost_insp_E = get_param('cost_insp_E')
    cost_ext = get_param('cost_ext')

    mode_fee_M = get_param('mode_fee_M')
    mode_fee_E = get_param('mode_fee_E')
    risk_penalty_M = get_param('risk_penalty_M')

    cost_insp_weight = get_param('cost_insp_weight')

    horizon_weeks = int(get_param('planning_horizon_weeks'))
    idle_tolerance = get_param('idle_tolerance')

    # Unit profit is based on original inspection and cost parameters for consistency
    cost_a = mfg_a * cost_mfg + asm_a * cost_asm + insp_a_orig * cost_insp_orig
    cost_b = mfg_b * cost_mfg + asm_b * cost_asm + insp_b_orig * cost_insp_orig
    profit_a = price_a - cost_a
    profit_b = price_b - cost_b

    weeks = list(range(1, horizon_weeks + 1))

    # Big-M constants
    # Maximum possible hours: use capacity as a safe upper bound
    M_insp = cap_insp + cap_ext
    M_prodA = cap_mfg / max(mfg_a, 1e-6)
    M_prodB = cap_asm / max(asm_b, 1e-6)
    M_big = max(M_insp, M_prodA, M_prodB, 100.0)

    # Stage 1: minimize idle time + risk penalty
    prob1 = pulp.LpProblem("Stage1_Minimize_Idle_And_Risk", pulp.LpMinimize)

    x_A = {t: pulp.LpVariable(f"x_A_{t}", lowBound=min_a, cat='Integer') for t in weeks}
    x_B = {t: pulp.LpVariable(f"x_B_{t}", lowBound=0, cat='Integer') for t in weeks}

    y_M = {t: pulp.LpVariable(f"y_M_{t}", lowBound=0, upBound=1, cat='Binary') for t in weeks}
    y_E = {t: pulp.LpVariable(f"y_E_{t}", lowBound=0, upBound=1, cat='Binary') for t in weeks}

    h_insp_M = {t: pulp.LpVariable(f"h_insp_M_{t}", lowBound=0) for t in weeks}
    h_insp_E = {t: pulp.LpVariable(f"h_insp_E_{t}", lowBound=0) for t in weeks}
    h_ext = {t: pulp.LpVariable(f"h_ext_{t}", lowBound=0) for t in weeks}

    idle_mfg = {t: pulp.LpVariable(f"idle_mfg_{t}") for t in weeks}
    idle_asm = {t: pulp.LpVariable(f"idle_asm_{t}") for t in weeks}
    idle_insp = {t: pulp.LpVariable(f"idle_insp_{t}") for t in weeks}

    for t in weeks:
        # Manufacturing capacity: only A consumes manufacturing hours
        prob1 += mfg_a * x_A[t] <= cap_mfg

        # Assembly capacity: A and B
        prob1 += asm_a * x_A[t] + asm_b * x_B[t] <= cap_asm

        # Mode selection: at most one
        prob1 += y_M[t] + y_E[t] <= 1

        # Manual inspection linking
        prob1 += h_insp_M[t] <= insp_a_M * x_A[t] + insp_b_M * x_B[t] + M_big * (1 - y_M[t])
        prob1 += h_insp_M[t] >= insp_a_M * x_A[t] + insp_b_M * x_B[t] - M_big * (1 - y_M[t])
        prob1 += h_insp_M[t] <= M_insp * y_M[t]

        # Enhanced inspection linking
        prob1 += h_insp_E[t] <= insp_a_E * x_A[t] + insp_b_E * x_B[t] + M_big * (1 - y_E[t])
        prob1 += h_insp_E[t] >= insp_a_E * x_A[t] + insp_b_E * x_B[t] - M_big * (1 - y_E[t])
        prob1 += h_insp_E[t] <= (cap_insp + cap_ext) * y_E[t]

        # External inspection capacity when Enhanced mode used
        prob1 += h_ext[t] <= cap_ext * y_E[t]

        # In-house inspection capacity
        prob1 += h_insp_M[t] + h_insp_E[t] <= cap_insp

        # Idle time definitions
        prob1 += idle_mfg[t] == cap_mfg - mfg_a * x_A[t]
        prob1 += idle_asm[t] == cap_asm - (asm_a * x_A[t] + asm_b * x_B[t])
        prob1 += idle_insp[t] == cap_insp - (h_insp_M[t] + h_insp_E[t])

        # Nonnegativity of idle times
        prob1 += idle_mfg[t] >= 0
        prob1 += idle_asm[t] >= 0
        prob1 += idle_insp[t] >= 0

        # Weekly profit >= min_weekly_profit (use profit_a,b as margin per unit)
        # Operating cost components considered in objective of stage 2, but here we ensure margin
        prob1 += profit_a * x_A[t] + profit_b * x_B[t] >= min_profit

    total_idle_cost = []
    for t in weeks:
        idle_cost_t = cost_mfg * idle_mfg[t] + cost_asm * idle_asm[t] + cost_insp_weight * idle_insp[t]
        risk_cost_t = risk_penalty_M * y_M[t]
        total_idle_cost.append(idle_cost_t + risk_cost_t)

    prob1 += pulp.lpSum(total_idle_cost)

    prob1.solve(pulp.GUROBI_CMD(msg=False))

    if pulp.LpStatus[prob1.status] != 'Optimal':
        raise RuntimeError('Stage 1 did not find an optimal solution')

    min_idle_val = pulp.value(prob1.objective)

    # Stage 2: maximize total profit subject to idle cost constraint
    prob2 = pulp.LpProblem("Stage2_Maximize_Profit", pulp.LpMaximize)

    x_A2 = {t: pulp.LpVariable(f"x_A2_{t}", lowBound=min_a, cat='Integer') for t in weeks}
    x_B2 = {t: pulp.LpVariable(f"x_B2_{t}", lowBound=0, cat='Integer') for t in weeks}

    y_M2 = {t: pulp.LpVariable(f"y_M2_{t}", lowBound=0, upBound=1, cat='Binary') for t in weeks}
    y_E2 = {t: pulp.LpVariable(f"y_E2_{t}", lowBound=0, upBound=1, cat='Binary') for t in weeks}

    h_insp_M2 = {t: pulp.LpVariable(f"h_insp_M2_{t}", lowBound=0) for t in weeks}
    h_insp_E2 = {t: pulp.LpVariable(f"h_insp_E2_{t}", lowBound=0) for t in weeks}
    h_ext2 = {t: pulp.LpVariable(f"h_ext2_{t}", lowBound=0) for t in weeks}

    idle_mfg2 = {t: pulp.LpVariable(f"idle_mfg2_{t}") for t in weeks}
    idle_asm2 = {t: pulp.LpVariable(f"idle_asm2_{t}") for t in weeks}
    idle_insp2 = {t: pulp.LpVariable(f"idle_insp2_{t}") for t in weeks}

    profit_t = {}

    for t in weeks:
        prob2 += mfg_a * x_A2[t] <= cap_mfg
        prob2 += asm_a * x_A2[t] + asm_b * x_B2[t] <= cap_asm

        prob2 += y_M2[t] + y_E2[t] <= 1

        prob2 += h_insp_M2[t] <= insp_a_M * x_A2[t] + insp_b_M * x_B2[t] + M_big * (1 - y_M2[t])
        prob2 += h_insp_M2[t] >= insp_a_M * x_A2[t] + insp_b_M * x_B2[t] - M_big * (1 - y_M2[t])
        prob2 += h_insp_M2[t] <= M_insp * y_M2[t]

        prob2 += h_insp_E2[t] <= insp_a_E * x_A2[t] + insp_b_E * x_B2[t] + M_big * (1 - y_E2[t])
        prob2 += h_insp_E2[t] >= insp_a_E * x_A2[t] + insp_b_E * x_B2[t] - M_big * (1 - y_E2[t])
        prob2 += h_insp_E2[t] <= (cap_insp + cap_ext) * y_E2[t]

        prob2 += h_ext2[t] <= cap_ext * y_E2[t]

        prob2 += h_insp_M2[t] + h_insp_E2[t] <= cap_insp

        prob2 += idle_mfg2[t] == cap_mfg - mfg_a * x_A2[t]
        prob2 += idle_asm2[t] == cap_asm - (asm_a * x_A2[t] + asm_b * x_B2[t])
        prob2 += idle_insp2[t] == cap_insp - (h_insp_M2[t] + h_insp_E2[t])

        prob2 += idle_mfg2[t] >= 0
        prob2 += idle_asm2[t] >= 0
        prob2 += idle_insp2[t] >= 0

        prob2 += profit_a * x_A2[t] + profit_b * x_B2[t] >= min_profit

        # Revenue
        revenue_t = price_a * x_A2[t] + price_b * x_B2[t]

        # Costs
        mfg_cost_t = cost_mfg * (mfg_a * x_A2[t])
        asm_cost_t = cost_asm * (asm_a * x_A2[t] + asm_b * x_B2[t])

        insp_cost_M_t = cost_insp_M * h_insp_M2[t]
        insp_cost_E_t = cost_insp_E * h_insp_E2[t]
        ext_cost_t = cost_ext * h_ext2[t]

        mode_fee_t = mode_fee_M * y_M2[t] + mode_fee_E * y_E2[t]
        risk_cost_t = risk_penalty_M * y_M2[t]

        insp_cost_t = insp_cost_M_t + insp_cost_E_t + ext_cost_t
        total_cost_t = mfg_cost_t + asm_cost_t + insp_cost_t + mode_fee_t + risk_cost_t

        profit_t[t] = revenue_t - total_cost_t

    total_idle_cost2_terms = []
    for t in weeks:
        idle_cost_t2 = cost_mfg * idle_mfg2[t] + cost_asm * idle_asm2[t] + cost_insp_weight * idle_insp2[t]
        risk_cost_t2 = risk_penalty_M * y_M2[t]
        total_idle_cost2_terms.append(idle_cost_t2 + risk_cost_t2)

    prob2 += pulp.lpSum(total_idle_cost2_terms) <= min_idle_val + idle_tolerance

    prob2 += pulp.lpSum([profit_t[t] for t in weeks])

    prob2.solve(pulp.GUROBI_CMD(msg=False))

    if pulp.LpStatus[prob2.status] != 'Optimal':
        raise RuntimeError('Stage 2 did not find an optimal solution')

    final_obj = pulp.value(prob2.objective)
    print(f"OBJECTIVE_VALUE: {round(final_obj, 4)}")


if __name__ == '__main__':
    solve()
