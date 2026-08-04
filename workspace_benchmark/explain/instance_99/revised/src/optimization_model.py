from gurobi_execution_record import install_gurobi_objective_recorder
install_gurobi_objective_recorder('Revise_99_revised')
import os
import sys
from itertools import product

# Add parent directory to path if needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import load_general_parameters, load_reliability_table


def solve():
    # Load data
    params = load_general_parameters()
    reliability = load_reliability_table()

    # Extract economic and physical parameters
    unit_price = [
        params['unit_price_component_1'],
        params['unit_price_component_2'],
        params['unit_price_component_3'],
    ]
    unit_weight = [
        params['unit_weight_component_1'],
        params['unit_weight_component_2'],
        params['unit_weight_component_3'],
    ]

    # Scenario-specific limits
    total_budget_A = params['total_budget_scenario_A']
    total_budget_B = params['total_budget_scenario_B']
    weight_limit_A = params['weight_limit_scenario_A']
    weight_limit_B = params['weight_limit_scenario_B']

    # Domain of spare counts comes from reliability table
    max_spares = max(reliability.keys())

    best_expected_reliability = -1.0
    best_combo = None

    # Enumerate all combinations of spares for 3 components
    for s1, s2, s3 in product(range(max_spares + 1), repeat=3):
        # Check that reliability data exists for each chosen spare count
        if s1 not in reliability or s2 not in reliability or s3 not in reliability:
            continue

        # Compute cost and weight based on installed spares (base units are not costed here)
        total_cost = (
            s1 * unit_price[0]
            + s2 * unit_price[1]
            + s3 * unit_price[2]
        )
        total_weight = (
            s1 * unit_weight[0]
            + s2 * unit_weight[1]
            + s3 * unit_weight[2]
        )

        # Scenario A constraints
        if total_cost > total_budget_A:
            continue
        if total_weight > weight_limit_A:
            continue

        # Scenario B constraints
        if total_cost > total_budget_B:
            continue
        if total_weight > weight_limit_B:
            continue

        # Retrieve component reliabilities (scenario-independent)
        r1 = reliability[s1][0]
        r2 = reliability[s2][1]
        r3 = reliability[s3][2]

        # System reliability in each scenario (identical here)
        sysrel_A = r1 * r2 * r3
        sysrel_B = sysrel_A  # same reliability mapping for both scenarios

        # Expected reliability with two equally likely scenarios
        expected_rel = 0.5 * sysrel_A + 0.5 * sysrel_B

        if expected_rel > best_expected_reliability:
            best_expected_reliability = expected_rel
            best_combo = (s1, s2, s3, total_cost, total_weight, r1, r2, r3)

    if best_combo is None:
        raise RuntimeError("No feasible spare configuration satisfies all scenario constraints.")

    s1, s2, s3, total_cost, total_weight, r1, r2, r3 = best_combo

    print(f"Optimal spare parts allocation (shared across scenarios): Component 1: {s1}, Component 2: {s2}, Component 3: {s3}")
    print(f"Total cost (both scenarios share this configuration): {total_cost}")
    print(f"Total weight (both scenarios share this configuration): {total_weight}")
    print(f"Component reliabilities (scenario-independent): {r1}, {r2}, {r3}")
    print(f"Scenario A system reliability: {r1 * r2 * r3}")
    print(f"Scenario B system reliability: {r1 * r2 * r3}")
    print(f"Expected system reliability (two equally likely scenarios): {best_expected_reliability}")
    # The objective value for evaluation is the expected reliability
    print(f"OBJECTIVE_VALUE: {best_expected_reliability}")


if __name__ == '__main__':
    solve()
