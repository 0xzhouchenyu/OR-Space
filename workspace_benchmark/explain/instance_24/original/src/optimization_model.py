import os
import csv
from gurobi_pulp_compat import *

def main():
    # Load data
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
    
    # Decision variables: number of trips for each vehicle type (integers)
    prob = LpProblem("Transportation_Pollution_Minimization", LpMinimize)
    
    x_truck = LpVariable("truck_trips", lowBound=0, cat='Integer')
    x_van = LpVariable("van_trips", lowBound=0, cat='Integer')
    x_moto = LpVariable("motorcycle_trips", lowBound=0, cat='Integer')
    x_ev = LpVariable("ev_trips", lowBound=0, cat='Integer')
    
    # Objective: minimize total pollution
    prob += truck_pollution * x_truck + van_pollution * x_van + motorcycle_pollution * x_moto + ev_pollution * x_ev, "Total_Pollution"
    
    # Constraint: all products must be delivered
    prob += truck_capacity * x_truck + van_capacity * x_van + motorcycle_capacity * x_moto + ev_capacity * x_ev >= product_units, "Demand"
    
    # Constraint: total pollution must not exceed maximum
    prob += truck_pollution * x_truck + van_pollution * x_van + motorcycle_pollution * x_moto + ev_pollution * x_ev <= max_total_pollution, "Max_Pollution"
    
    # Constraint: minimum truck trips
    prob += x_truck >= min_truck_trips, "Min_Truck_Trips"
    
    # Solve
    prob.solve(GUROBI_CMD(msg=0))
    
    # Print solution details
    print(f"Status: {LpStatus[prob.status]}")
    print(f"Truck trips: {value(x_truck)}")
    print(f"Van trips: {value(x_van)}")
    print(f"Motorcycle trips: {value(x_moto)}")
    print(f"EV trips: {value(x_ev)}")
    
    total_capacity = (value(x_truck) * truck_capacity + value(x_van) * van_capacity + 
                      value(x_moto) * motorcycle_capacity + value(x_ev) * ev_capacity)
    print(f"Total capacity delivered: {total_capacity}")
    
    obj_val = value(prob.objective)
    print(f"OBJECTIVE_VALUE: {obj_val}")

if __name__ == "__main__":
    main()