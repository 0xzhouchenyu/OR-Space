import os

def get_data_path(filename):
    """
    Returns the absolute path to a file in the data directory.
    """
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', filename)