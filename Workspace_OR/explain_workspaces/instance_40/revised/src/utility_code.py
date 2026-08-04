import os
import pandas as pd

def load_parameters():
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'general_parameters.csv')
    df = pd.read_csv(csv_path)
    return dict(zip(df['Parameter_Name'], df['Value']))