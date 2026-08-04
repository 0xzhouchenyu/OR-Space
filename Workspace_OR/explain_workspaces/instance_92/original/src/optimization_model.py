import os
from utils import load_parameters
import gurobi_pulp_compat as pulp

# Load data
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
params = load_parameters(os.path.join(data_dir, 'general_parameters.csv'))

num_students = int(params['num_students'])
num_buses = int(params['num_buses'])
bus_capacity = int(params['bus_capacity'])
num_minibuses = int(params['num_minibuses'])
minibus_capacity = int(params['minibus_capacity'])
num_drivers = int(params['num_drivers'])
bus_rental_cost = float(params['bus_rental_cost'])
minibus_rental_cost = float(params['minibus_rental_cost'])

# Create the optimization model
prob = pulp.LpProblem("SchoolTrip", pulp.LpMinimize)

# Decision variables
x = pulp.LpVariable("buses", lowBound=0, upBound=num_buses, cat='Integer')
y = pulp.LpVariable("minibuses", lowBound=0, upBound=num_minibuses, cat='Integer')

# Objective: minimize total rental cost
prob += bus_rental_cost * x + minibus_rental_cost * y, "TotalCost"

# Constraints
# Must transport all students
prob += bus_capacity * x + minibus_capacity * y >= num_students, "StudentCapacity"

# Total vehicles (drivers) constraint
prob += x + y <= num_drivers, "DriverLimit"

# Solve
prob.solve(pulp.GUROBI_CMD(msg=0))

# Output results
obj_val = pulp.value(prob.objective)
print(f"Buses: {int(pulp.value(x))}")
print(f"Minibuses: {int(pulp.value(y))}")
print(f"OBJECTIVE_VALUE: {obj_val}")