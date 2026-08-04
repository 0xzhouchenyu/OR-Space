import os
import csv

def load_data():
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    
    students = []
    with open(os.path.join(base, 'table_1.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            s = {'Student_ID': int(row['Student_ID']),
                 'Wage_CNY_per_hour': float(row['Wage_CNY_per_hour'])}
            for d in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
                s[d] = float(row[d])
            students.append(s)
    
    params = {}
    with open(os.path.join(base, 'general_parameters.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['Parameter_Name']
            val = row['Value']
            try:
                params[name] = int(val)
            except ValueError:
                try:
                    params[name] = float(val)
                except ValueError:
                    params[name] = val
    
    return students, params