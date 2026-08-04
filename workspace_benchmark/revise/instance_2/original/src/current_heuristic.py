from gurobi_execution_record import install_gurobi_objective_recorder
install_gurobi_objective_recorder('Advanced_2')
import os
import csv
from utils import load_parameters

data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

params = load_parameters(os.path.join(data_dir, 'general_parameters.csv'))

a1 = params['a1']
a2 = params['a2']
training_capacity = params['training_capacity_per_jet']
training_duration = params['training_duration']

# Maximize total pilots trained over the 2-year training program
# Year 1 training jets: x1 <= a1
# Year 2 training jets: x2 <= a1 + a2 (total available jets)
# But training jets in year 1 continue in year 2, so year 2 training jets >= x1
# Total pilots = training_capacity * (x1 + x2) where x1 jets train in yr1, x2 in yr2
# With x1 continuing into year 2: total training in year 2 = x1 + new jets for training
# Pilots trained = training_capacity * (x1 + x2) with x2 = total training jets in year 2
# Maximize: 5*(x1 + x2), x1 <= 10, x2 <= 10+15=25, x1<=x2 (year1 jets continue)
# Max: x1=10, x2=15 → 5*25=125

total_pilots = training_capacity * (a1 + a2)
print(f"Year 1 training jets: {a1}")
print(f"Year 2 training jets: {a2}")
print(f"Total pilots trained: {total_pilots}")
print(f"OBJECTIVE_VALUE: {total_pilots}")