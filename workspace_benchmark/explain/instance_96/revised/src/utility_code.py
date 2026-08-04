import os

def get_data_paths():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    table_1_path = os.path.join(data_dir, 'table_1.csv')
    params_path = os.path.join(data_dir, 'general_parameters.csv')
    return table_1_path, params_path
