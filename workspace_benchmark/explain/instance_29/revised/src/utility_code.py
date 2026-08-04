import os

def get_data_path(filename):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', filename)