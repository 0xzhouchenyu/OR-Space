import os
import pandas as pd

def load_data():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    
    t1 = pd.read_csv(os.path.join(data_dir, 'table_1.csv'))
    t2 = pd.read_csv(os.path.join(data_dir, 'table_2.csv'))
    t3 = pd.read_csv(os.path.join(data_dir, 'table_3.csv'))
    gp = pd.read_csv(os.path.join(data_dir, 'general_parameters.csv'))
    
    # Merge product data
    df = t1.merge(t2, on='Product').merge(t3, on='Product')
    
    # Parse general parameters
    prod_days = float(gp[gp['Parameter_Name'] == 'production_days']['Value'].iloc[0])
    
    return df, prod_days