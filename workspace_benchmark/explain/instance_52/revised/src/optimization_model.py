import os
import csv
from gurobi_pulp_compat import LpProblem, LpMinimize, LpVariable, lpSum, LpInteger, value, GUROBI_CMD


def read_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, '..', 'data')

    # Read shift requirements
    shifts = []
    with open(os.path.join(data_dir, 'table_1_2.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            shifts.append({
                'shift': int(row['Shift']),
                'time': row['Time'],
                'required': int(row['Required_number'])
            })

    n = len(shifts)
    required = [s['required'] for s in shifts]

    # Read general parameters
    params = {}
    with open(os.path.join(data_dir, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['Parameter_Name']
            val = row['Value']
            # store as float
            try:
                params[name] = float(val)
            except ValueError:
                params[name] = val

    return n, required, params


def build_and_solve():
    n, required, params = read_data()

    shift_duration = int(params['shift_duration'])
    periods_per_shift = shift_duration // 4

    max_night_driver_fraction = float(params['max_night_driver_fraction'])
    max_night_crew_fraction = float(params['max_night_crew_fraction'])
    max_overtime_shifts = float(params['max_overtime_shifts'])
    overtime_cost_factor = float(params['overtime_cost_factor'])

    prob = LpProblem('DriverCrewStaffingWithOvertime', LpMinimize)

    # Decision variables
    x_driver = [LpVariable(f"x_driver_{i+1}", lowBound=0, cat=LpInteger) for i in range(n)]
    x_crew = [LpVariable(f"x_crew_{i+1}", lowBound=0, cat=LpInteger) for i in range(n)]
    y_driver = [LpVariable(f"y_driver_{i+1}", lowBound=0, cat=LpInteger) for i in range(n)]
    y_crew = [LpVariable(f"y_crew_{i+1}", lowBound=0, cat=LpInteger) for i in range(n)]

    # Objective: minimize regular shifts + overtime_cost_factor * overtime shifts
    total_regular = lpSum(x_driver) + lpSum(x_crew)
    total_overtime = lpSum(y_driver) + lpSum(y_crew)
    prob += total_regular + overtime_cost_factor * total_overtime

    # Coverage constraints for each period j
    for j in range(n):
        driver_cover_terms = []
        crew_cover_terms = []
        for i in range(n):
            covered_periods = [((i + k) % n) for k in range(periods_per_shift)]
            if j in covered_periods:
                driver_cover_terms.append(x_driver[i] + y_driver[i])
                crew_cover_terms.append(x_crew[i] + y_crew[i])
        prob += lpSum(driver_cover_terms) >= required[j], f"DriverDemand_period_{j+1}"
        prob += lpSum(crew_cover_terms) >= required[j], f"CrewDemand_period_{j+1}"

    # Night fraction constraints
    night_indices = [4, 5]  # zero-based indices for periods 5 and 6

    total_driver = lpSum(x_driver)
    night_driver = x_driver[night_indices[0]] + x_driver[night_indices[1]]
    prob += night_driver <= max_night_driver_fraction * total_driver, "MaxNightDriverFraction"

    total_crew = lpSum(x_crew)
    night_crew = x_crew[night_indices[0]] + x_crew[night_indices[1]]
    prob += night_crew <= max_night_crew_fraction * total_crew, "MaxNightCrewFraction"

    # Overtime capacity constraint
    prob += total_overtime <= max_overtime_shifts, "MaxOvertimeShifts"

    # Solve
    prob.solve(GUROBI_CMD(msg=0))

    obj_val = value(prob.objective)

    # Optional: print some solution details for debugging
    for i in range(n):
        dv = x_driver[i]
        cv = x_crew[i]
        dov = y_driver[i]
        cov = y_crew[i]
        print(f"Period {i+1}: x_driver={dv.value()}, x_crew={cv.value()}, y_driver={dov.value()}, y_crew={cov.value()}")

    print(f"OBJECTIVE_VALUE: {obj_val}")


if __name__ == '__main__':
    build_and_solve()
