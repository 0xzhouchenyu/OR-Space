import os

def get_data_dir():
    # In the revised problem, data is located one level up in the 'data' directory.
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
