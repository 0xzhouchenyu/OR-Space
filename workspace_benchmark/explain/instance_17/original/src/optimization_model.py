import math
from utils import load_data, fuel_per_heavy_bomb, fuel_per_light_bomb, prob_destroy_part, prob_at_least_k
from gurobi_execution_record import install_gurobi_objective_recorder


install_gurobi_objective_recorder("BombAllocationExactSearch")


def main():
    parts, params = load_data()

    max_heavy = int(params['max_heavy_bombs'])
    max_light = int(params['max_light_bombs'])
    fuel_limit = params['fuel_limit']
    min_parts = int(params['min_parts_destroyed'])
    n = len(parts)

    fuel_h = [fuel_per_heavy_bomb(p['distance'], params) for p in parts]
    fuel_l = [fuel_per_light_bomb(p['distance'], params) for p in parts]

    print(f"Fuel per heavy bomb per part: {fuel_h}")
    print(f"Fuel per light bomb per part: {fuel_l}")

    best_obj = 0.0
    best_alloc = []
    alloc = []

    def evaluate(candidate):
        probs = [
            prob_destroy_part(candidate[i][0], candidate[i][1], parts[i]['p_heavy'], parts[i]['p_light'])
            for i in range(n)
        ]
        return prob_at_least_k(probs, min_parts)

    def search(idx, remaining_heavy, remaining_light, remaining_fuel):
        nonlocal best_obj, best_alloc
        if idx == n:
            obj = evaluate(alloc)
            if obj > best_obj:
                best_obj = obj
                best_alloc = list(alloc)
            return

        max_h_here = min(remaining_heavy, int(remaining_fuel / fuel_h[idx]))
        max_l_here = min(remaining_light, int(remaining_fuel / fuel_l[idx]))

        for xh in range(max_h_here + 1):
            fuel_used_h = xh * fuel_h[idx]
            if fuel_used_h > remaining_fuel:
                break
            for xl in range(max_l_here + 1):
                fuel_used = fuel_used_h + xl * fuel_l[idx]
                if fuel_used > remaining_fuel:
                    break
                alloc.append((xh, xl))
                search(
                    idx + 1,
                    remaining_heavy - xh,
                    remaining_light - xl,
                    remaining_fuel - fuel_used,
                )
                alloc.pop()

    search(0, max_heavy, max_light, fuel_limit)

    total_heavy = sum(item[0] for item in best_alloc)
    total_light = sum(item[1] for item in best_alloc)
    total_fuel = sum(best_alloc[i][0] * fuel_h[i] + best_alloc[i][1] * fuel_l[i] for i in range(n))
    print(f"Best allocation: {best_alloc}")
    print(f"Total heavy bombs used: {total_heavy}")
    print(f"Total light bombs used: {total_light}")
    print(f"Total fuel used: {total_fuel}")
    print(f"OBJECTIVE_VALUE: {best_obj:.4f}")


if __name__ == '__main__':
    main()
