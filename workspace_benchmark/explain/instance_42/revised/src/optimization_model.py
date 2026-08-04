import os
import gurobi_pulp_compat as pulp
from utils import load_parameters

def main():
    # Load parameters
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    params = load_parameters(os.path.join(data_dir, 'general_parameters.csv'))

    a = params['a']              # hours per batch, method 1
    b = params['b']              # hours per batch, method 2
    k = params['k']              # tons per batch
    d = params['d']              # minimum production (tons)
    c_off = params['c_offpeak']  # per-furnace off-peak hours
    c_peak = params['c_peak']    # per-furnace peak hours
    cap_off = params['cap_offpeak']  # plant-wide off-peak hours
    cap_peak = params['cap_peak']    # plant-wide peak hours

    m_off = params['m_offpeak']  # cost method 1 off-peak
    m_peak = params['m_peak']    # cost method 1 peak
    n_off = params['n_offpeak']  # cost method 2 off-peak
    n_peak = params['n_peak']    # cost method 2 peak

    f_off = params['f_offpeak']  # activation off-peak
    f_peak = params['f_peak']    # activation peak
    offpeak_cooldown_threshold = params['offpeak_cooldown_batch_threshold']
    offpeak_cooldown_fee = params['offpeak_cooldown_fee']

    # Big-M values derived from time caps
    min_time_per_batch = min(a, b)
    M_off = cap_off / min_time_per_batch if min_time_per_batch > 0 else 0.0
    M_peak = cap_peak / min_time_per_batch if min_time_per_batch > 0 else 0.0

    prob = pulp.LpProblem("SteelFurnace_Peak_Offpeak_Activation", pulp.LpMinimize)

    furnaces = [1, 2]

    # Decision variables
    x1_off = {i: pulp.LpVariable(f"x_{i}_1_off", lowBound=0) for i in furnaces}
    x2_off = {i: pulp.LpVariable(f"x_{i}_2_off", lowBound=0) for i in furnaces}
    x1_peak = {i: pulp.LpVariable(f"x_{i}_1_peak", lowBound=0) for i in furnaces}
    x2_peak = {i: pulp.LpVariable(f"x_{i}_2_peak", lowBound=0) for i in furnaces}

    y_off = {i: pulp.LpVariable(f"y_{i}_off", lowBound=0, upBound=1, cat='Binary') for i in furnaces}
    y_peak = {i: pulp.LpVariable(f"y_{i}_peak", lowBound=0, upBound=1, cat='Binary') for i in furnaces}
    cooldown = {i: pulp.LpVariable(f"cooldown_{i}_off", lowBound=0, upBound=1, cat='Binary') for i in furnaces}

    # Objective: variable fuel costs + activation costs
    prob += (
        pulp.lpSum(
            m_off * x1_off[i] + m_peak * x1_peak[i] +
            n_off * x2_off[i] + n_peak * x2_peak[i] +
            f_off * y_off[i] + f_peak * y_peak[i] + offpeak_cooldown_fee * cooldown[i]
            for i in furnaces
        ),
        "TotalCost"
    )

    # 1. Per-furnace time-cap constraints
    for i in furnaces:
        # Off-peak per-furnace
        prob += a * x1_off[i] + b * x2_off[i] <= c_off, f"Furnace_{i}_Offpeak_Time"
        # Peak per-furnace
        prob += a * x1_peak[i] + b * x2_peak[i] <= c_peak, f"Furnace_{i}_Peak_Time"

    # 2. Plant-wide shared time caps
    prob += (
        a * (x1_off[1] + x1_off[2]) + b * (x2_off[1] + x2_off[2]) <= cap_off,
        "Plant_Offpeak_Time"
    )
    prob += (
        a * (x1_peak[1] + x1_peak[2]) + b * (x2_peak[1] + x2_peak[2]) <= cap_peak,
        "Plant_Peak_Time"
    )

    # 3. Activation linking constraints
    for i in furnaces:
        prob += x1_off[i] + x2_off[i] <= M_off * y_off[i], f"Offpeak_Activation_Link_{i}"
        prob += x1_peak[i] + x2_peak[i] <= M_peak * y_peak[i], f"Peak_Activation_Link_{i}"
        prob += x1_off[i] + x2_off[i] <= offpeak_cooldown_threshold + M_off * cooldown[i], f"Offpeak_Cooldown_{i}"

    # 4. Minimum production requirement
    total_batches = (
        x1_off[1] + x2_off[1] + x1_peak[1] + x2_peak[1] +
        x1_off[2] + x2_off[2] + x1_peak[2] + x2_peak[2]
    )
    prob += k * total_batches >= d, "Min_Production"

    # Solve
    prob.solve(pulp.GUROBI_CMD(msg=0))

    obj_val = pulp.value(prob.objective)

    # Print only the required line for evaluation
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()
