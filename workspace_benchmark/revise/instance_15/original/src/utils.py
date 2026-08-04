import os
import pandas as pd

def load_data():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    table_1 = pd.read_csv(os.path.join(data_dir, 'table_1.csv'))
    params = pd.read_csv(os.path.join(data_dir, 'general_parameters.csv'))
    
    param_dict = dict(zip(params['Parameter_Name'], params['Value']))
    demand = dict(zip(table_1['stage'], table_1['tool_requirement']))
    
    return param_dict, demand