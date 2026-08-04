import os
import sys
import gurobi_pulp_compat as pulp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import load_demand, load_parameters


def main():
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

    demand_data = load_demand(base_dir)
    params = load_parameters(base_dir)

    months = ["July", "August", "September", "October", "November", "December"]
    products = ["Product_I", "Product_II"]

    prod_cost = {
        "Product_I": params["product_I_cost_jun_to_dec"],
        "Product_II": params["product_II_cost_jun_to_dec"],
    }
    volume = {
        "Product_I": params["product_I_volume"],
        "Product_II": params["product_II_volume"],
    }
    machine_hours = {
        "Product_I": params["product_I_machine_hours"],
        "Product_II": params["product_II_machine_hours"],
    }
    power_kwh = {
        "Product_I": params["product_I_power_kwh"],
        "Product_II": params["product_II_power_kwh"],
    }

    machine_cap = params["machine_hours_capacity_monthly"]
    warehouse_cap = params["warehouse_capacity"]
    own_wh_cost = params["own_warehouse_cost"]
    grid_cost = params["grid_electricity_cost"]
    gen_cost = params["generator_electricity_cost"]
    initial_inventory = params["initial_inventory_july"]

    grid_quota = {
        "July": params["grid_quota_july"],
        "August": params["grid_quota_august"],
        "September": params["grid_quota_september"],
        "October": params["grid_quota_october"],
        "November": params["grid_quota_november"],
        "December": params["grid_quota_december"],
    }
    generator_max = {
        "July": params["generator_max_july"],
        "August": params["generator_max_august"],
        "September": params["generator_max_september"],
        "October": params["generator_max_october"],
        "November": params["generator_max_november"],
        "December": params["generator_max_december"],
    }

    demand = {(m, p): demand_data[(m, p)] for m in months for p in products}

    prob = pulp.LpProblem("Production_Planning_With_Electricity_Quota_OwnWarehouseOnly", pulp.LpMinimize)

    # Monthly production and end-of-month inventory
    prod = pulp.LpVariable.dicts(
        "prod",
        [(m, p) for m in months for p in products],
        lowBound=0,
        cat="Continuous"
    )
    inv = pulp.LpVariable.dicts(
        "inv",
        [(m, p) for m in months for p in products],
        lowBound=0,
        cat="Continuous"
    )

    # Electricity sourcing
    grid_power = pulp.LpVariable.dicts("grid_power", months, lowBound=0, cat="Continuous")
    gen_power = pulp.LpVariable.dicts("gen_power", months, lowBound=0, cat="Continuous")

    # Own warehouse usage only; external warehouse is not allowed in the revised model
    own_wh = pulp.LpVariable.dicts("own_wh", months, lowBound=0, cat="Continuous")

    # Objective: production cost + own warehouse cost + electricity cost
    prob += (
        pulp.lpSum(prod_cost[p] * prod[(m, p)] for m in months for p in products)
        + pulp.lpSum(own_wh_cost * own_wh[m] for m in months)
        + pulp.lpSum(grid_cost * grid_power[m] + gen_cost * gen_power[m] for m in months)
    ), "Total_Cost"

    for idx, m in enumerate(months):
        prev_m = months[idx - 1] if idx > 0 else None

        # Inventory balance and on-time demand satisfaction
        for p in products:
            beginning_inventory = initial_inventory if prev_m is None else inv[(prev_m, p)]
            prob += (
                beginning_inventory + prod[(m, p)] - demand[(m, p)] == inv[(m, p)]
            ), f"Inventory_Balance_{m}_{p}"

        # Product-specific machine-hour capacity
        prob += (
            pulp.lpSum(machine_hours[p] * prod[(m, p)] for p in products) <= machine_cap
        ), f"Machine_Hours_{m}"

        # Own warehouse only: total inventory volume must fit in the factory warehouse
        prob += (
            own_wh[m] == pulp.lpSum(volume[p] * inv[(m, p)] for p in products)
        ), f"Own_Warehouse_Usage_{m}"
        prob += own_wh[m] <= warehouse_cap, f"Own_Warehouse_Capacity_{m}"

        # Electricity source limits and supply balance
        prob += grid_power[m] <= grid_quota[m], f"Grid_Quota_{m}"
        prob += gen_power[m] <= generator_max[m], f"Generator_Capacity_{m}"
        prob += (
            grid_power[m] + gen_power[m]
            >= pulp.lpSum(power_kwh[p] * prod[(m, p)] for p in products)
        ), f"Electricity_Supply_{m}"

    prob.solve(pulp.GUROBI_CMD(msg=0))

    print(f"Status: {pulp.LpStatus[prob.status]}")
    for m in months:
        print(
            f"{m}: "
            f"prod_I={pulp.value(prod[(m, 'Product_I')]):.2f}, "
            f"prod_II={pulp.value(prod[(m, 'Product_II')]):.2f}, "
            f"inv_I={pulp.value(inv[(m, 'Product_I')]):.2f}, "
            f"inv_II={pulp.value(inv[(m, 'Product_II')]):.2f}, "
            f"own_wh={pulp.value(own_wh[m]):.2f}, "
            f"grid={pulp.value(grid_power[m]):.2f}, "
            f"generator={pulp.value(gen_power[m]):.2f}"
        )

    obj_val = pulp.value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj_val:.2f}")


if __name__ == "__main__":
    main()
