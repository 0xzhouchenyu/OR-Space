import os
from utils import load_parameters

try:
    import gurobi_pulp_compat as pulp
except ImportError:
    raise ImportError("PuLP is required to run this script.")


def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    params = load_parameters(os.path.join(data_dir, 'general_parameters.csv'))

    a1 = params['a1']
    a2 = params['a2']
    training_capacity = params['training_capacity_per_jet']
    training_duration = params['training_duration']  # kept for completeness
    dual_eff = params['dual_use_training_efficiency']
    training_cap = params['training_intensity_cap']
    combat_min_y2 = params['combat_jet_min_year2']
    combat_weight = params['combat_weight']
    training_weight = params['training_weight']

    total_jets_y2 = a1 + a2

    # Define MILP model
    model = pulp.LpProblem('Jet_Training_Combat_Planning', pulp.LpMaximize)

    # Decision variables (integers)
    T1 = pulp.LpVariable('T1', lowBound=0, cat=pulp.LpInteger)
    C1 = pulp.LpVariable('C1', lowBound=0, cat=pulp.LpInteger)
    D1 = pulp.LpVariable('D1', lowBound=0, cat=pulp.LpInteger)

    T2 = pulp.LpVariable('T2', lowBound=0, cat=pulp.LpInteger)
    C2 = pulp.LpVariable('C2', lowBound=0, cat=pulp.LpInteger)
    D2 = pulp.LpVariable('D2', lowBound=0, cat=pulp.LpInteger)

    P1 = pulp.LpVariable('P1', lowBound=0, cat=pulp.LpInteger)
    P2 = pulp.LpVariable('P2', lowBound=0, cat=pulp.LpInteger)

    # Objective: maximize combat_weight * (C2 + D2) + training_weight * (P1 + P2)
    model += combat_weight * (C2 + D2) + training_weight * (P1 + P2), 'Objective_Readiness'

    # 1) Jet availability constraints
    model += T1 + C1 + D1 == a1, 'JetBalance_Year1'
    model += T2 + C2 + D2 == total_jets_y2, 'JetBalance_Year2'

    # 2) Training capacity constraints
    model += P1 <= training_capacity * T1 + dual_eff * training_capacity * D1, 'TrainCapacity_Y1'
    model += P2 <= training_capacity * T2 + dual_eff * training_capacity * D2, 'TrainCapacity_Y2'

    # 3) Pilot-combat matching in year 2
    model += C2 + D2 <= P1, 'PilotMatch_Y2'

    # 4) Training intensity constraints
    model += T1 + D1 <= training_cap * a1, 'TrainIntensity_Y1'
    model += T2 + D2 <= training_cap * total_jets_y2, 'TrainIntensity_Y2'

    # 5) Minimum combat jets in year 2
    model += C2 + D2 >= combat_min_y2, 'MinCombat_Y2'

    # Solve model using Gurobi
    solver = pulp.GUROBI_CMD(msg=False)
    result_status = model.solve(solver)

    if pulp.LpStatus[result_status] != 'Optimal':
        raise RuntimeError(f"Optimization did not find an optimal solution: {pulp.LpStatus[result_status]}")

    objective_value = pulp.value(model.objective)

    print(f"OBJECTIVE_VALUE: {objective_value}")


if __name__ == '__main__':
    main()
