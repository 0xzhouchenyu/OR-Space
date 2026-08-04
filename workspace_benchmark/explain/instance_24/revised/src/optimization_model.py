import os
import csv
from gurobi_pulp_compat import *

def main():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row['Parameter_Name'].strip()] = float(row['Value'].strip())

    product_units = params['product_units']
    truck_pollution = params['truck_pollution']
    van_pollution = params['van_pollution']
    motorcycle_pollution = params['motorcycle_pollution']
    ev_pollution = params['electric_vehicle_pollution']
    max_total_pollution = params['max_total_pollution']
    min_truck_trips = params['min_truck_trips']
    truck_capacity = params['truck_capacity']
    van_capacity = params['van_capacity']
    motorcycle_capacity = params['motorcycle_capacity']
    ev_capacity = params['electric_vehicle_capacity']

    sales_point_share_sp1 = params['sales_point_share_sp1']
    sales_point_share_sp2 = params['sales_point_share_sp2']
    sales_point_share_sp3 = params['sales_point_share_sp3']

    min_truck_share_sp1 = params['min_truck_share_sp1']
    min_truck_share_sp2 = params['min_truck_share_sp2']
    min_truck_share_sp3 = params['min_truck_share_sp3']

    M_truck_sp_day = params['M_truck_sp_day']
    M_ev_sp_day = params['M_ev_sp_day']
    M_van_sp_day = params['M_van_sp_day']
    M_moto_sp_day = params['M_moto_sp_day']

    # Define sets
    sales_points = ['SP1', 'SP2', 'SP3']
    days = [1, 2, 3]

    sp_shares = {
        'SP1': sales_point_share_sp1,
        'SP2': sales_point_share_sp2,
        'SP3': sales_point_share_sp3
    }

    min_truck_share = {
        'SP1': min_truck_share_sp1,
        'SP2': min_truck_share_sp2,
        'SP3': min_truck_share_sp3
    }

    demand_sp = {sp: sp_shares[sp] * product_units for sp in sales_points}

    prob = LpProblem("Transportation_Pollution_Minimization_SP_Mode", LpMinimize)

    # Decision variables
    x_truck = LpVariable.dicts("truck_trips", (sales_points, days), lowBound=0, cat='Integer')
    x_van = LpVariable.dicts("van_trips", (sales_points, days), lowBound=0, cat='Integer')
    x_moto = LpVariable.dicts("motorcycle_trips", (sales_points, days), lowBound=0, cat='Integer')
    x_ev = LpVariable.dicts("ev_trips", (sales_points, days), lowBound=0, cat='Integer')

    z_mode = LpVariable.dicts("exclusive_mode_sp", (sales_points, days), lowBound=0, upBound=1, cat='Binary')

    # Objective: minimize total pollution across all SP and days
    prob += (
        lpSum(truck_pollution * x_truck[sp][d] for sp in sales_points for d in days)
        + lpSum(van_pollution * x_van[sp][d] for sp in sales_points for d in days)
        + lpSum(motorcycle_pollution * x_moto[sp][d] for sp in sales_points for d in days)
        + lpSum(ev_pollution * x_ev[sp][d] for sp in sales_points for d in days)
    ), "Total_Pollution"

    # Demand satisfaction per sales point
    for sp in sales_points:
        prob += (
            lpSum(truck_capacity * x_truck[sp][d] for d in days)
            + lpSum(van_capacity * x_van[sp][d] for d in days)
            + lpSum(motorcycle_capacity * x_moto[sp][d] for d in days)
            + lpSum(ev_capacity * x_ev[sp][d] for d in days)
            >= demand_sp[sp]
        ), f"Demand_{sp}"

    # Global pollution cap
    prob += (
        lpSum(truck_pollution * x_truck[sp][d] for sp in sales_points for d in days)
        + lpSum(van_pollution * x_van[sp][d] for sp in sales_points for d in days)
        + lpSum(motorcycle_pollution * x_moto[sp][d] for sp in sales_points for d in days)
        + lpSum(ev_pollution * x_ev[sp][d] for sp in sales_points for d in days)
        <= max_total_pollution
    ), "Max_Total_Pollution"

    # Global minimum truck trips across all SP and days
    prob += (
        lpSum(x_truck[sp][d] for sp in sales_points for d in days) >= min_truck_trips
    ), "Min_Total_Truck_Trips"

    # Mode-selection constraints with big-M
    for sp in sales_points:
        for d in days:
            # truck and ev only if z_mode == 1
            prob += x_truck[sp][d] <= M_truck_sp_day * z_mode[sp][d], f"Truck_Mode_{sp}_{d}"
            prob += x_ev[sp][d] <= M_ev_sp_day * z_mode[sp][d], f"EV_Mode_{sp}_{d}"
            # van and moto only if z_mode == 0
            prob += x_van[sp][d] <= M_van_sp_day * (1 - z_mode[sp][d]), f"Van_Mode_{sp}_{d}"
            prob += x_moto[sp][d] <= M_moto_sp_day * (1 - z_mode[sp][d]), f"Moto_Mode_{sp}_{d}"

    # Truck share constraints per sales point
    for sp in sales_points:
        total_trips_sp = (
            lpSum(x_truck[sp][d] for d in days)
            + lpSum(x_van[sp][d] for d in days)
            + lpSum(x_moto[sp][d] for d in days)
            + lpSum(x_ev[sp][d] for d in days)
        )
        prob += (
            lpSum(x_truck[sp][d] for d in days)
            >= min_truck_share[sp] * total_trips_sp
        ), f"Min_Truck_Share_{sp}"

    prob.solve(GUROBI_CMD(msg=0))

    status = LpStatus[prob.status]
    print(f"Status: {status}")
    for sp in sales_points:
        for d in days:
            print(f"{sp} Day {d} - Truck: {value(x_truck[sp][d])}, Van: {value(x_van[sp][d])}, Moto: {value(x_moto[sp][d])}, EV: {value(x_ev[sp][d])}, Mode: {value(z_mode[sp][d])}")

    total_capacity = 0.0
    for sp in sales_points:
        for d in days:
            total_capacity += (
                value(x_truck[sp][d]) * truck_capacity
                + value(x_van[sp][d]) * van_capacity
                + value(x_moto[sp][d]) * motorcycle_capacity
                + value(x_ev[sp][d]) * ev_capacity
            )
    print(f"Total capacity delivered: {total_capacity}")

    obj_val = value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()
