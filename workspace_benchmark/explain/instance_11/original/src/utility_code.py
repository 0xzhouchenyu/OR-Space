# Minimal utils file as requested
def get_data_path(filename):
    import os
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', filename)