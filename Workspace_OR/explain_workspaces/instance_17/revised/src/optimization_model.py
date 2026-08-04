from gurobi_execution_record import install_gurobi_objective_recorder
install_gurobi_objective_recorder('Revise_17_revised')
import math
from utils import load_data, fuel_per_heavy_bomb, fuel_per_light_bomb, prob_destroy_part, prob_at_least_k


def main():
    parts, params = load_data()

    max_heavy = int(params['max_heavy_bombs'])
    max_light = int(params['max_light_bombs'])
    fuel_limit = params['fuel_limit']
    min_parts = int(params['min_parts_destroyed'])
    max_sorties_A = int(params['max_sorties_A'])
    max_sorties_B = int(params['max_sorties_B'])
    overhead_A = params['sortie_fuel_overhead_A']
    overhead_B = params['sortie_fuel_overhead_B']
    scen_A = params['scenario_prob_A']
    scen_B = params['scenario_prob_B']

    n = len(parts)

    # Base per-sortie fuel (outward + return + takeoff/landing), same for both fleets.
    fuel_h_base = [fuel_per_heavy_bomb(p['distance'], params) for p in parts]
    fuel_l_base = [fuel_per_light_bomb(p['distance'], params) for p in parts]

    # Fleet-specific fuel per sortie = base + fleet overhead.
    fuel_h_A = [f + overhead_A for f in fuel_h_base]
    fuel_l_A = [f + overhead_A for f in fuel_l_base]
    fuel_h_B = [f + overhead_B for f in fuel_h_base]
    fuel_l_B = [f + overhead_B for f in fuel_l_base]

    # Pre-compute dominant (tighter) fuel bound for pruning.
    fuel_h_tight = [max(fuel_h_A[i], fuel_h_B[i]) for i in range(n)]
    fuel_l_tight = [max(fuel_l_A[i], fuel_l_B[i]) for i in range(n)]

    # Robust sortie cap = min of the two scenarios.
    max_total_sorties = min(max_sorties_A, max_sorties_B)

    def robust_feasible(xH, xL):
        if sum(xH) > max_heavy or sum(xL) > max_light:
            return False
        total_sorties = sum(xH) + sum(xL)
        if total_sorties > max_total_sorties:
            return False
        fuel_A = sum(xH[i] * fuel_h_A[i] + xL[i] * fuel_l_A[i] for i in range(n))
        fuel_B = sum(xH[i] * fuel_h_B[i] + xL[i] * fuel_l_B[i] for i in range(n))
        return fuel_A <= fuel_limit and fuel_B <= fuel_limit

    best = [0.0]
    alloc = []

    def search(idx, rem_heavy, rem_light, rem_sorties):
        if idx == n:
            xH = [a[0] for a in alloc]
            xL = [a[1] for a in alloc]
            if not robust_feasible(xH, xL):
                return
            probs = [
                prob_destroy_part(xH[i], xL[i], parts[i]['p_heavy'], parts[i]['p_light'])
                for i in range(n)
            ]
            p_succ = prob_at_least_k(probs, min_parts)
            # Since the bomb allocation is identical in both scenarios,
            # expected success = scen_A * p_succ + scen_B * p_succ = p_succ.
            obj = scen_A * p_succ + scen_B * p_succ
            if obj > best[0]:
                best[0] = obj
            return

        p_h = parts[idx]['p_heavy']
        p_l = parts[idx]['p_light']
        # Cap per-part bombs where marginal gain is negligible.
        if p_h > 0:
            useful_h = int(math.log(0.001) / math.log(1 - p_h)) + 1
        else:
            useful_h = 0
        if p_l > 0:
            useful_l = int(math.log(0.001) / math.log(1 - p_l)) + 1
        else:
            useful_l = 0
        useful_h = min(useful_h, rem_heavy, rem_sorties)
        useful_l = min(useful_l, rem_light, rem_sorties)

        for xh in range(useful_h + 1):
            if xh * fuel_h_tight[idx] > fuel_limit:
                break
            for xl in range(useful_l + 1):
                if xh + xl > rem_sorties:
                    break
                alloc.append((xh, xl))
                search(idx + 1, rem_heavy - xh, rem_light - xl, rem_sorties - xh - xl)
                alloc.pop()

    search(0, max_heavy, max_light, max_total_sorties)

    print("OBJECTIVE_VALUE:", round(best[0], 4))


if __name__ == '__main__':
    main()
